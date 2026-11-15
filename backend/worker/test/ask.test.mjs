import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createService } from "../src/service.js";
import { handleAsk, retrieve } from "../src/ask.js";

const bundle = JSON.parse(readFileSync(new URL("../../data/build/evidence_bundle.json", import.meta.url)));
const service = createService(bundle);
const VENT_Q = "How did BASS-II and Saffire-V flames respond when ventilation was reduced or stopped?";
const KEY = "test-key-should-never-leak";

function geminiStub(reply, capture) {
  return async (url, init) => {
    capture && capture.push({ url, init });
    return new Response(JSON.stringify({ candidates: [{ content: { parts: [{ text: JSON.stringify(reply) }] } }], usageMetadata: { totalTokenCount: 1 } }), { status: 200 });
  };
}
const params = (o) => new URLSearchParams(o);

test("ventilation question retrieves CMP-05 and both BASS-II and Saffire IV-V findings", () => {
  const { pack } = retrieve(service, bundle, VENT_Q);
  const ids = pack.map((r) => r.id);
  assert.ok(ids.includes("CMP-05"), ids.join(","));
  const studies = new Set(pack.filter((r) => r.type === "finding").map((r) => r.study_id));
  assert.ok(studies.has("BASS-II") && studies.has("SAFFIRE-IV-V"), [...studies].join(","));
  for (const r of pack.filter((x) => x.type === "finding")) {
    assert.ok(r.evidence_class && r.sources.length && Array.isArray(r.limitations));
  }
});

test("Gemini receives only the retrieved evidence pack, and the key travels in a header only", async () => {
  const cap = [];
  const { pack } = retrieve(service, bundle, VENT_Q);
  const reply = { supported: true, answer: "BASS-II flames went out when flow stopped [CMP-05]; Saffire V flames did not reliably [CMP-05].", cited_ids: ["CMP-05"], unsupported_reason: "" };
  const [status, body] = await handleAsk(service, bundle, { GEMINI_API_KEY: KEY }, params({ q: VENT_Q }), geminiStub(reply, cap));
  assert.equal(status, 200);
  assert.equal(cap.length, 1);
  assert.ok(!cap[0].url.includes(KEY));
  assert.equal(cap[0].init.headers["x-goog-api-key"], KEY);
  const sent = JSON.parse(cap[0].init.body).contents[0].parts[0].text;
  assert.ok(sent.includes(JSON.stringify(pack)));
  assert.equal(body.data.supported, true);
  assert.equal(body.data.citations[0].id, "CMP-05");
  assert.ok(!JSON.stringify(body).includes(KEY));
  assert.equal(body.meta.grounding, "verified_citations");
});

test("answers citing records that were not retrieved are rejected", async () => {
  const reply = { supported: true, answer: "Something [F-FAKE-99].", cited_ids: ["F-FAKE-99"] };
  const [status, body] = await handleAsk(service, bundle, { GEMINI_API_KEY: KEY }, params({ q: VENT_Q }), geminiStub(reply));
  assert.equal(status, 200);
  assert.equal(body.data.supported, false);
  assert.equal(body.data.citations.length, 0);
  assert.ok(!body.data.answer.includes("Something"));
});

test("answers with no citations are rejected", async () => {
  const reply = { supported: true, answer: "Fans are always safe to turn off.", cited_ids: [] };
  const [, body] = await handleAsk(service, bundle, { GEMINI_API_KEY: KEY }, params({ q: VENT_Q }), geminiStub(reply));
  assert.equal(body.data.supported, false);
  assert.ok(!body.data.answer.includes("always safe"));
});

test("model-declared unsupported questions are reported as unsupported", async () => {
  const reply = { supported: false, answer: "The evidence has no lunar data.", cited_ids: [], unsupported_reason: "No Moon or Mars evidence." };
  const [, body] = await handleAsk(service, bundle, { GEMINI_API_KEY: KEY }, params({ q: "What oxygen level is safe on the Moon?" }), geminiStub(reply));
  assert.equal(body.data.supported, false);
  assert.equal(body.data.citations.length, 0);
});

test("questions with no matching evidence never call Gemini", async () => {
  let called = false;
  const [status, body] = await handleAsk(service, bundle, { GEMINI_API_KEY: KEY }, params({ q: "basketball playoffs" }), async () => { called = true; });
  assert.equal(status, 200);
  assert.equal(called, false);
  assert.equal(body.data.supported, false);
  assert.equal(body.meta.grounding, "no_evidence_retrieved");
});

test("missing secret returns 503 with retrieved evidence and no Gemini call", async () => {
  let called = false;
  const [status, body] = await handleAsk(service, bundle, {}, params({ q: VENT_Q }), async () => { called = true; });
  assert.equal(status, 503);
  assert.equal(called, false);
  assert.equal(body.error.code, "assistant_unavailable");
  assert.ok(body.error.details.retrieved.some((r) => r.id === "CMP-05"));
});

test("upstream failure returns 502 without leaking the key", async () => {
  const bad = async () => new Response(JSON.stringify({ error: { message: "API key not valid" } }), { status: 400 });
  const [status, body] = await handleAsk(service, bundle, { GEMINI_API_KEY: KEY }, params({ q: VENT_Q }), bad);
  assert.equal(status, 502);
  assert.equal(body.error.code, "upstream_error");
  assert.ok(!JSON.stringify(body).includes(KEY));
});

test("input validation matches the API contract style", async () => {
  const s = async (o) => (await handleAsk(service, bundle, {}, new URLSearchParams(o)))[1].error.code;
  assert.equal(await s({}), "missing_parameter");
  assert.equal(await s({ q: "x".repeat(301) }), "invalid_parameter");
  assert.equal(await s({ q: "airflow", foo: "1" }), "unknown_parameter");
  assert.equal(await s([["q", "a"], ["q", "b"]]), "duplicate_parameter");
});

function rawStub(candidate) {
  return async () => new Response(JSON.stringify({ candidates: [candidate], usageMetadata: { totalTokenCount: 1 } }), { status: 200 });
}

test("newer Gemini replies: thought parts are ignored and the answer part is used", async () => {
  const reply = { supported: true, answer: "BASS-II flames went out when the fan stopped [CMP-05].", cited_ids: ["CMP-05"], unsupported_reason: "" };
  const cand = { content: { parts: [{ text: "internal reasoning, not JSON {", thought: true }, { text: JSON.stringify(reply) }] }, finishReason: "STOP" };
  const [status, body] = await handleAsk(service, bundle, { GEMINI_API_KEY: KEY }, params({ q: VENT_Q }), rawStub(cand));
  assert.equal(status, 200);
  assert.equal(body.meta.grounding, "verified_citations");
  assert.ok(body.data.citations.some((c) => c.id === "CMP-05"));
});

test("JSON wrapped in prose is still recovered; truncated output is reported with finish_reason", async () => {
  const reply = { supported: true, answer: "See [CMP-05].", cited_ids: ["CMP-05"], unsupported_reason: "" };
  const wrapped = { content: { parts: [{ text: "Here is the JSON:\n" + JSON.stringify(reply) + "\nDone." }] }, finishReason: "STOP" };
  const [ok] = await handleAsk(service, bundle, { GEMINI_API_KEY: KEY }, params({ q: VENT_Q }), rawStub(wrapped));
  assert.equal(ok, 200);
  const cut = { content: { parts: [{ text: '{"supported": true, "answer": "BASS-II fla' }] }, finishReason: "MAX_TOKENS" };
  const [status, body] = await handleAsk(service, bundle, { GEMINI_API_KEY: KEY }, params({ q: VENT_Q }), rawStub(cut));
  assert.equal(status, 502);
  assert.equal(body.error.code, "upstream_error");
  assert.equal(body.error.details.finish_reason, "MAX_TOKENS");
  assert.ok(!JSON.stringify(body).includes(KEY));
});

test("request asks for enough output room for thinking models", async () => {
  const cap = [];
  const reply = { supported: true, answer: "[CMP-05]", cited_ids: ["CMP-05"], unsupported_reason: "" };
  await handleAsk(service, bundle, { GEMINI_API_KEY: KEY }, params({ q: VENT_Q }), geminiStub(reply, cap));
  const cfg = JSON.parse(cap[0].init.body).generationConfig;
  assert.ok(cfg.maxOutputTokens >= 4096);
  assert.match(cap[0].url, /gemini-3\.5-flash:generateContent$/);
});
