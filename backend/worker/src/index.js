// Cloudflare Worker entry. Serves the evidence bundle built by `python -m ember.build`.
// wrangler bundles the JSON at deploy time; there is no database and no external call.
import bundle from "../../data/build/evidence_bundle.json";
import { createService } from "./service.js";
import { handleAsk } from "./ask.js";

const service = createService(bundle);

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
  "Access-Control-Max-Age": "86400",
};

export function respond(request) {
  if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });
  const url = new URL(request.url);
  let path = url.pathname;
  try {
    path = decodeURIComponent(path);
  } catch {
    // keep the raw path; it will 404
  }
  const [status, body] = service.handle(request.method, path, [...url.searchParams]);
  const headers = {
    ...CORS,
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": status === 200 ? "public, max-age=300" : "no-store",
    "X-Evidence-Bundle": bundle.manifest.content_sha256.slice(0, 16),
  };
  return new Response(request.method === "HEAD" ? null : JSON.stringify(body), { status, headers });
}

const ASK_PATH = "/api/v1/ask";

// Ask ARCAUS: the only route that calls an outside service. Kept separate from the
// deterministic evidence routes so a model or key problem can never affect them.
export async function respondAsk(request, env, fetchImpl) {
  const url = new URL(request.url);
  const headers = { ...CORS, "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store",
    "X-Evidence-Bundle": bundle.manifest.content_sha256.slice(0, 16) };
  if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });
  if (request.method !== "GET" && request.method !== "HEAD") {
    return new Response(JSON.stringify({ error: { code: "method_not_allowed", message: "Use GET", details: { allowed: ["GET", "HEAD", "OPTIONS"] } } }), { status: 405, headers });
  }
  // Cost protection: per-visitor limit on Gemini-backed questions (Workers Rate Limiting binding ASK_LIMITER).
  // Fails open if the binding is absent (local tests) or the limiter errors, so the evidence API is never blocked.
  if (env && env.ASK_LIMITER && typeof env.ASK_LIMITER.limit === "function") {
    let allowed = true;
    try {
      const key = request.headers.get("CF-Connecting-IP") || "unknown";
      ({ success: allowed } = await env.ASK_LIMITER.limit({ key: `ask:${key}` }));
    } catch { allowed = true; }
    if (!allowed) {
      return new Response(JSON.stringify({ error: { code: "rate_limited", message: "Too many questions in a short time. Please wait a minute and try again. The evidence explorer still works.", details: { limit: "10 per minute per visitor" } } }),
        { status: 429, headers: { ...headers, "Retry-After": "60" } });
    }
  }
  const [status, body] = await handleAsk(service, bundle, env, url.searchParams, fetchImpl);
  return new Response(request.method === "HEAD" ? null : JSON.stringify(body), { status, headers });
}

export default {
  async fetch(request, env) {
    try {
      if (new URL(request.url).pathname === ASK_PATH) return await respondAsk(request, env, fetch);
      return respond(request);
    } catch (err) {
      return new Response(JSON.stringify({ error: { code: "internal_error", message: "Unexpected server error", details: {} } }), {
        status: 500, headers: { ...CORS, "Content-Type": "application/json; charset=utf-8" },
      });
    }
  },
};
