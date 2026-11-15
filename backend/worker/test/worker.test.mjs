// Exercises the Worker fetch entry (CORS, HEAD, OPTIONS, headers) by loading index.js
// with the bundle JSON injected through a data: URL import map substitute.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, writeFileSync, mkdtempSync, cpSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const root = new URL("../../", import.meta.url);
const dir = mkdtempSync(join(tmpdir(), "ember-worker-"));
cpSync(new URL("worker/src/", root), join(dir, "src"), { recursive: true });
const bundleJs = "export default " + readFileSync(new URL("data/build/evidence_bundle.json", root), "utf8") + ";\n";
writeFileSync(join(dir, "bundle.mjs"), bundleJs);
const idx = readFileSync(join(dir, "src", "index.js"), "utf8").replace('"../../data/build/evidence_bundle.json"', '"../bundle.mjs"');
writeFileSync(join(dir, "src", "index.mjs"), idx);
const workerMod = await import(join(dir, "src", "index.mjs"));
const worker = workerMod.default;
const { respondAsk } = workerMod;
const KEY = "test-key-should-never-leak";

test("GET returns JSON with CORS and bundle header", async () => {
  const r = await worker.fetch(new Request("https://w.test/api/v1/health"));
  assert.equal(r.status, 200);
  assert.equal(r.headers.get("access-control-allow-origin"), "*");
  assert.match(r.headers.get("content-type"), /application\/json/);
  assert.equal(r.headers.get("x-evidence-bundle").length, 16);
  const j = await r.json();
  assert.equal(j.data.status, "ok");
});

test("OPTIONS preflight returns 204", async () => {
  const r = await worker.fetch(new Request("https://w.test/api/v1/findings", { method: "OPTIONS" }));
  assert.equal(r.status, 204);
  assert.match(r.headers.get("access-control-allow-methods"), /GET/);
});

test("HEAD returns no body", async () => {
  const r = await worker.fetch(new Request("https://w.test/api/v1/findings", { method: "HEAD" }));
  assert.equal(r.status, 200);
  assert.equal(await r.text(), "");
});

test("errors are not cached", async () => {
  const r = await worker.fetch(new Request("https://w.test/api/v1/findings/NOPE"));
  assert.equal(r.status, 404);
  assert.equal(r.headers.get("cache-control"), "no-store");
});

test("POST is rejected", async () => {
  const r = await worker.fetch(new Request("https://w.test/api/v1/findings", { method: "POST", body: "{}" }));
  assert.equal(r.status, 405);
});

test("encoded query values decode like the Python service", async () => {
  const r = await worker.fetch(new Request("https://w.test/api/v1/bass2/fabric/outcomes?outcome_class=quenched%20(low%20flow)"));
  assert.equal((await r.json()).meta.count, 6);
});

test("rate limiter: over-limit visitors get 429 before Gemini is called; evidence untouched", async () => {
  let calls = 0;
  const fetchSpy = async () => { calls++; return new Response("{}", { status: 500 }); };
  const blocked = { ASK_LIMITER: { limit: async ({ key }) => { assert.equal(key, "ask:203.0.113.9"); return { success: false }; } }, GEMINI_API_KEY: KEY };
  const req = new Request("https://x/api/v1/ask?q=ventilation", { headers: { "CF-Connecting-IP": "203.0.113.9" } });
  const res = await respondAsk(req, blocked, fetchSpy);
  assert.equal(res.status, 429);
  assert.equal(res.headers.get("Access-Control-Allow-Origin"), "*");
  assert.equal(res.headers.get("Retry-After"), "60");
  assert.equal((await res.json()).error.code, "rate_limited");
  assert.equal(calls, 0);
});
test("rate limiter: fails open when the limiter errors or is absent", async () => {
  const broken = { ASK_LIMITER: { limit: async () => { throw new Error("down"); } } };
  const r1 = await respondAsk(new Request("https://x/api/v1/ask?q=ventilation"), broken, fetch);
  assert.equal(r1.status, 503); // reaches normal handling (no key configured) rather than being blocked
  const r2 = await respondAsk(new Request("https://x/api/v1/ask?q=ventilation"), {}, fetch);
  assert.equal(r2.status, 503);
  const pre = await respondAsk(new Request("https://x/api/v1/ask", { method: "OPTIONS" }), { ASK_LIMITER: { limit: async () => ({ success: false }) } }, fetch);
  assert.equal(pre.status, 204); // CORS preflight never rate-limited
});
