// Ask ARCAUS: evidence-grounded explanations.
// Flow: deterministic BM25 retrieval over the bundle -> evidence pack -> Gemini (only the pack) -> citation checks.
// Gemini never sees anything that the evidence API did not return, and its answer is rejected
// unless every citation points at a retrieved record. The API key lives only in the Worker secret GEMINI_API_KEY.

export const ASK_MAX_Q = 300;
const DEFAULT_MODEL = "gemini-3.5-flash";
const MAX_FINDINGS = 6;
const MAX_COMPARISONS = 2;

export const GUARDRAILS = [
  "Answers use only retrieved ARCAUS evidence records; anything else is reported as unsupported.",
  "No fire-risk predictions, safe thresholds, operating guidance, or Moon/Mars extrapolation.",
  "Measurements from different experiments (BASS-II, Saffire, SoFIE-GEL) are never merged numerically.",
  "Evidence classes are kept: verified measurement, NASA author conclusion, hypothesis.",
];

const SYSTEM = `You are the Ask ARCAUS research assistant for an independent NASA Space Apps 2026 project.
You explain microgravity combustion evidence to judges and students.
RULES (mandatory):
1. Use ONLY the EVIDENCE records provided in the user message. Do not use outside knowledge, even if you know it.
2. Every factual sentence must be supported by at least one record id from EVIDENCE. Cite ids like [F-B2-03] or [CMP-05].
3. Keep each record's evidence class explicit: "verified measurement", "NASA author conclusion", or "hypothesis". Never present a hypothesis or author conclusion as a measured result.
4. State experimental conditions (atmosphere, pressure, oxygen, flow, material) when you compare experiments, and say they differ when they differ.
5. Never combine or average numbers from different experiments. Never infer safe thresholds, fire-risk predictions, operating procedures, or Moon/Mars/lunar behaviour.
6. If the EVIDENCE does not answer the question, set "supported" to false and say plainly what is missing. Do not guess.
7. Mention the most important limitations from the records.
Return JSON only: {"supported": boolean, "answer": string (<= 220 words, plain text, with [ID] citations), "cited_ids": [string], "unsupported_reason": string}`;

function compactFinding(f, sources) {
  return {
    id: f.id, type: "finding", study: f.study_name, study_id: f.study_id,
    evidence_type: f.evidence_type, evidence_class: f.evidence_type_label, independence_from_bass2: f.independence_from_bass2,
    statement: f.statement, material: f.material || null, geometry: f.geometry || null,
    conditions: f.conditions || {}, reported_values: f.reported_values || [],
    limitations: f.limitations || [],
    sources: (f.source_refs || []).map((r) => {
      const s = sources[r.source_id];
      return { source_id: r.source_id, title: s ? s.title : null, locator: r.locator, url: s ? s.url : null };
    }),
  };
}

function compactComparison(c) {
  return {
    id: c.id, type: "comparison", title: c.title, question: c.question,
    agreement: c.agreement, differences: c.differences,
    independent_experiment_count: c.independent_experiment_count, independence_note: c.independence_note,
    numeric_merge_allowed: c.numeric_merge_allowed, numeric_merge_reason: c.numeric_merge_reason,
    limitations: c.limitations || [], finding_ids: c.finding_ids,
  };
}

// Deterministic retrieval through the existing evidence service (same BM25 as /search).
export function retrieve(service, bundle, q) {
  const [status, body] = service.handle("GET", "/api/v1/search", [["q", q], ["type", "all"], ["limit", "12"]]);
  if (status !== 200) return { terms: [], hits: [], pack: [] };
  const findings = Object.fromEntries(bundle.findings.map((f) => [f.id, f]));
  const comps = Object.fromEntries(bundle.comparisons.map((c) => [c.id, c]));
  const sources = Object.fromEntries(bundle.sources.map((s) => [s.id, s]));
  const hits = body.data.results;
  const compIds = hits.filter((h) => h.type === "comparison").slice(0, MAX_COMPARISONS).map((h) => h.id);
  // Findings: top-ranked hits first, then members of the retrieved comparisons, so a comparison is never cited without its rows.
  const fIds = [];
  for (const h of hits) if (h.type === "finding" && !fIds.includes(h.id)) fIds.push(h.id);
  for (const cid of compIds) for (const fid of comps[cid].finding_ids) if (!fIds.includes(fid)) fIds.push(fid);
  const pack = [
    ...compIds.map((id) => compactComparison(comps[id])),
    ...fIds.slice(0, MAX_FINDINGS + 4 * compIds.length).filter((id) => findings[id]).map((id) => compactFinding(findings[id], sources)),
  ];
  return { terms: body.data.terms, hits, pack };
}

function citationsFor(ids, pack) {
  const byId = Object.fromEntries(pack.map((r) => [r.id, r]));
  return ids.filter((id) => byId[id]).map((id) => {
    const r = byId[id];
    return r.type === "finding"
      ? { id, type: "finding", study: r.study, evidence_type: r.evidence_type, evidence_class: r.evidence_class, statement: r.statement,
          conditions: r.conditions, limitations: r.limitations, sources: r.sources }
      : { id, type: "comparison", title: r.title, independent_experiment_count: r.independent_experiment_count,
          independence_note: r.independence_note, numeric_merge_reason: r.numeric_merge_reason, limitations: r.limitations };
  });
}

async function callGemini(env, q, pack, fetchImpl) {
  const model = env.GEMINI_MODEL || DEFAULT_MODEL;
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent`;
  const payload = {
    systemInstruction: { parts: [{ text: SYSTEM }] },
    contents: [{ role: "user", parts: [{ text: `QUESTION: ${q}\n\nEVIDENCE (JSON):\n${JSON.stringify(pack)}` }] }],
    generationConfig: { temperature: 0.1, maxOutputTokens: 900, responseMimeType: "application/json" },
  };
  const res = await fetchImpl(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-goog-api-key": env.GEMINI_API_KEY },
    body: JSON.stringify(payload),
  });
  const text = await res.text();
  if (!res.ok) {
    let msg = "Gemini request failed";
    try { msg = JSON.parse(text).error.message || msg; } catch { /* keep generic */ }
    const err = new Error(msg); err.upstreamStatus = res.status; throw err;
  }
  const out = JSON.parse(text);
  const raw = out?.candidates?.[0]?.content?.parts?.map((p) => p.text || "").join("") || "";
  let parsed;
  try { parsed = JSON.parse(raw.replace(/^```(?:json)?\s*|\s*```$/g, "")); } catch { parsed = null; }
  return { model, parsed, usage: out.usageMetadata || null };
}

export async function handleAsk(service, bundle, env, searchParams, fetchImpl = fetch) {
  const meta = { bundle_version: bundle.manifest.bundle_version, content_sha256: bundle.manifest.content_sha256 };
  const err = (status, code, message, details = {}) => [status, { error: { code, message, details } }];
  const keys = [...searchParams.keys()];
  const unknown = keys.filter((k) => k !== "q");
  if (unknown.length) return err(400, "unknown_parameter", `Unknown parameter '${unknown[0]}'`, { parameter: unknown[0], allowed: ["q"] });
  if (searchParams.getAll("q").length > 1) return err(400, "duplicate_parameter", "Parameter 'q' was given more than once", { parameter: "q" });
  const q = (searchParams.get("q") || "").trim();
  if (!q) return err(400, "missing_parameter", "Missing required parameter 'q'", { parameter: "q" });
  if (q.length > ASK_MAX_Q) return err(400, "invalid_parameter", `'q' must be at most ${ASK_MAX_Q} characters`, { parameter: "q", max: ASK_MAX_Q });

  const { terms, pack } = retrieve(service, bundle, q);
  const retrieved = pack.map((r) => ({ id: r.id, type: r.type }));
  const base = { query: q, retrieval: { method: "BM25 via /api/v1/search (deterministic)", terms, retrieved }, guardrails: GUARDRAILS };

  if (!pack.length) {
    return [200, { data: { ...base, supported: false, answer: "ARCAUS has no NASA evidence records that match this question, so it cannot answer it. Try asking about BASS-II flame spread, extinction, oxygen, airflow or ventilation changes.", citations: [], model: null },
      meta: { ...meta, grounding: "no_evidence_retrieved", generated_by: "rule" } }];
  }
  if (!env || !env.GEMINI_API_KEY) {
    return err(503, "assistant_unavailable", "The Gemini assistant is not configured on this Worker (GEMINI_API_KEY secret missing). Retrieved evidence is listed in details.", { retrieved });
  }

  let g;
  try {
    g = await callGemini(env, q, pack, fetchImpl);
  } catch (e) {
    return err(502, "upstream_error", "The language model did not return an answer. The evidence API itself is unaffected.", { upstream_status: e.upstreamStatus || null, retrieved });
  }
  const p = g.parsed;
  if (!p || typeof p.answer !== "string") {
    return err(502, "upstream_error", "The language model returned an unreadable answer.", { retrieved });
  }
  const allowed = new Set(pack.map((r) => r.id));
  const inText = [...p.answer.matchAll(/\[([A-Z]+-[A-Z0-9-]+)\]/g)].map((m) => m[1]);
  const claimed = [...new Set([...(Array.isArray(p.cited_ids) ? p.cited_ids : []), ...inText])];
  const valid = claimed.filter((id) => allowed.has(id));
  const invalid = claimed.filter((id) => !allowed.has(id));
  // An answer that cites nothing it was given, or cites records it was not given, is not grounded.
  const grounded = p.supported === true && valid.length > 0 && invalid.length === 0;
  const answer = grounded ? p.answer : (p.supported === true
    ? "The model's answer could not be verified against the retrieved evidence, so it is withheld. The records ARCAUS found are listed below."
    : (p.answer || p.unsupported_reason || "The retrieved evidence does not answer this question."));
  return [200, { data: { ...base, supported: grounded, answer, unsupported_reason: grounded ? null : (p.unsupported_reason || (invalid.length ? `Cited records not in evidence: ${invalid.join(", ")}` : "Not supported by retrieved evidence")),
      citations: citationsFor(grounded ? valid : [], pack), model: g.model, usage: g.usage },
    meta: { ...meta, grounding: grounded ? "verified_citations" : "rejected_or_unsupported", generated_by: "gemini+citation_check" } }];
}
