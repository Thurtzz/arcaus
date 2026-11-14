// Port of ember/service.py. Keep the two in step: any change here needs the same
// change there, and the parity test will fail until they agree.
import { makeTokenizer, queryTerms, round4, scoreDoc } from "./search.js";

const PREFIX = "/api/v1";
const EVIDENCE_TYPES = ["verified_measurement", "author_conclusion", "hypothesis"];
const INDEPENDENCE = ["same_experiment", "same_lineage", "separate_experiment_shared_team", "separate_investigation"];
const TOPICS = ["airflow", "oxygen", "geometry", "extinction_mechanism", "ventilation_change", "combustion_products",
  "ignition", "materials", "detection", "dataset_scope"];
const OUTCOMES = ["quenched (low flow)", "blow-off (high flow)", "burned, no extinction limit reached", "no ignition"];
const FLOW_CFG = ["Opposed", "Concurrent", "Stagnation", "unresolved"];
const ACCESS = ["full_text", "full_text_extraction", "abstract_only", "dataset"];
const SEARCH_TYPES = ["all", "finding", "study", "comparison"];

class ApiError extends Error {
  constructor(status, code, message, details) {
    super(message);
    this.status = status; this.code = code; this.details = details || {};
  }
}
const errBody = (e) => ({ error: { code: e.code, message: e.message, details: e.details } });
const has = (o, k) => Object.prototype.hasOwnProperty.call(o, k);

function parseOne(name, raw, spec) {
  const kind = spec[0];
  if (kind === "str") {
    const v = raw.trim();
    if (!v || v.length > spec[1]) throw new ApiError(400, "invalid_parameter", `'${name}' must be 1-${spec[1]} characters`, { parameter: name });
    return v;
  }
  if (kind === "enum") {
    if (!spec[1].includes(raw)) throw new ApiError(400, "invalid_parameter", `'${name}' must be one of the allowed values`, { parameter: name, allowed: spec[1] });
    return raw;
  }
  if (kind === "int") {
    if (!/^-?\d+$/.test(raw)) throw new ApiError(400, "invalid_parameter", `'${name}' must be an integer`, { parameter: name });
    const v = parseInt(raw, 10);
    if (v < spec[1] || v > spec[2]) throw new ApiError(400, "invalid_parameter", `'${name}' must be between ${spec[1]} and ${spec[2]}`, { parameter: name, min: spec[1], max: spec[2] });
    return v;
  }
  if (kind === "num") {
    if (!/^-?\d+(\.\d+)?$/.test(raw)) throw new ApiError(400, "invalid_parameter", `'${name}' must be a number`, { parameter: name });
    return parseFloat(raw);
  }
  if (kind === "bool") {
    if (raw !== "true" && raw !== "false") throw new ApiError(400, "invalid_parameter", `'${name}' must be 'true' or 'false'`, { parameter: name });
    return raw === "true";
  }
  throw new Error(kind);
}

function parseParams(pairs, specs, required = []) {
  const seen = new Map();
  for (const [k, v] of pairs) {
    if (!has(specs, k)) throw new ApiError(400, "unknown_parameter", `Unknown query parameter '${k}'`, { parameter: k, allowed: Object.keys(specs).sort() });
    if (seen.has(k)) throw new ApiError(400, "duplicate_parameter", `Query parameter '${k}' given more than once`, { parameter: k });
    seen.set(k, v);
  }
  for (const r of required) {
    if (!seen.has(r)) throw new ApiError(400, "missing_parameter", `Query parameter '${r}' is required`, { parameter: r });
  }
  const out = {};
  for (const [k, v] of seen) out[k] = parseOne(k, v, specs[k]);
  return out;
}

const feq = (a, b) => a !== null && a !== undefined && Math.abs(a - b) < 1e-9;
const pick = (o, keys) => Object.fromEntries(keys.map((k) => [k, o[k]]));
const byId = (rows, key = "id") => Object.fromEntries(rows.map((r) => [r[key], r]));

export function createService(bundle) {
  const b = bundle;
  const studies = byId(b.studies), sources = byId(b.sources), findings = byId(b.findings);
  const comparisons = byId(b.comparisons), tests = byId(b.bass2.tests, "test_id");
  const index = b.search_index;
  const tokenize = makeTokenizer(index.config);

  const meta = (extra) => ({ bundle_version: b.manifest.bundle_version, content_sha256: b.manifest.content_sha256, ...(extra || {}) });
  const list = (rows, p, extra) => ({ data: rows, meta: meta({ count: rows.length, filters: p, ...(extra || {}) }) });
  const one = (rec, extra) => ({ data: rec, meta: meta(extra) });
  const get = (table, key, kind) => {
    if (!has(table, key)) throw new ApiError(404, "not_found", `No ${kind} with id '${key}'`, { id: key });
    return table[key];
  };
  const findingSummary = (f) => pick(f, ["id", "title", "study_id", "evidence_type", "evidence_type_label", "independence_from_bass2", "topics"]);
  const terms = (q) => {
    const t = queryTerms(tokenize, q);
    if (!t.length) throw new ApiError(400, "invalid_parameter", "'q' has no searchable terms after removing stopwords", { parameter: "q" });
    return t;
  };

  const h = {
    root: () => one({ service: "EMBER / ORBIT evidence service", api_version: "v1", endpoints: routes.filter((r) => r[0]).map((r) => PREFIX + r[0]) }),
    health: () => {
      const c = b.consistency;
      return one({ status: c.failed === 0 ? "ok" : "degraded", checks_passed: c.passed, checks_failed: c.failed, generated_at: b.manifest.generated_at });
    },
    meta: () => one({ ...b.manifest, units: b.units, evidence_labels: b.evidence_labels, independence_levels: b.independence_levels }),
    listStudies: (p) => list(b.studies.filter((s) => (!has(p, "lineage") || s.lineage_group === p.lineage)
      && (!has(p, "independence") || s.independence_from_bass2 === p.independence)), p),
    getStudy: (id) => {
      const s = get(studies, id, "study");
      return one({ ...s, sources: s.source_ids.map((x) => sources[x]), findings: s.finding_ids.map((f) => findingSummary(findings[f])) });
    },
    listSources: (p) => list(b.sources.filter((s) => !has(p, "access") || s.access === p.access), p),
    getSource: (id) => {
      const s = get(sources, id, "source");
      const cited = b.findings.filter((f) => f.source_refs.some((r) => r.source_id === id)).map((f) => f.id);
      return one({ ...s, cited_by_findings: cited });
    },
    listFindings: (p) => list(b.findings.filter((f) => (!has(p, "study") || f.study_id === p.study)
      && (!has(p, "topic") || f.topics.includes(p.topic))
      && (!has(p, "evidence_type") || f.evidence_type === p.evidence_type)
      && (!has(p, "independence") || f.independence_from_bass2 === p.independence)
      && (!has(p, "lineage") || f.lineage_group === p.lineage)
      && (!has(p, "test_id") || f.test_ids.includes(p.test_id))), p),
    getFinding: (id) => {
      const f = get(findings, id, "finding");
      const st = studies[f.study_id];
      return one({
        ...f,
        source_refs: f.source_refs.map((r) => ({ ...r, source: sources[r.source_id] })),
        study: pick(st, ["id", "name", "platform", "lineage_group", "independence_from_bass2", "data_in_service"]),
        comparisons: b.comparisons.filter((c) => c.finding_ids.includes(id)).map((c) => c.id),
        gaps: b.gaps.filter((g) => g.related_findings.includes(id)).map((g) => g.id),
      });
    },
    listComparisons: (p) => list(b.comparisons.filter((c) => !has(p, "topic") || c.topic === p.topic), p),
    getComparison: (id) => {
      const c = get(comparisons, id, "comparison");
      const rows = c.finding_ids.map((fid) => {
        const f = findings[fid];
        return { finding_id: fid, study_id: f.study_id, study_name: f.study_name, lineage_group: f.lineage_group,
          independence_from_bass2: f.independence_from_bass2, evidence_type: f.evidence_type, title: f.title,
          statement: f.statement, material: f.material, geometry: f.geometry, conditions: f.conditions, source_refs: f.source_refs };
      });
      return one({ ...c, rows });
    },
    listGaps: (p) => list(b.gaps.filter((g) => (!has(p, "status") || g.status === p.status)
      && (!has(p, "priority") || g.priority === p.priority) && (!has(p, "study") || g.study_id === p.study)), p),
    consistency: (p) => {
      const c = b.consistency;
      return list(c.checks.filter((x) => !has(p, "status") || x.status === p.status), p, { passed: c.passed, failed: c.failed });
    },
    search: (p) => {
      const t = terms(p.q);
      const typ = has(p, "type") ? p.type : "all", limit = has(p, "limit") ? p.limit : 10;
      const hits = [];
      for (const d of index.docs) {
        if (typ !== "all" && d.type !== typ) continue;
        if (has(p, "evidence_type") && d.evidence_type !== p.evidence_type) continue;
        if (has(p, "study") && d.study_id !== p.study) continue;
        const [s, matched] = scoreDoc(d, t, index);
        if (s > 0) hits.push({ id: d.id, type: d.type, title: d.title, study_id: d.study_id, evidence_type: d.evidence_type, score: round4(s), matched_terms: matched });
      }
      hits.sort((x, y) => (y.score - x.score) || (x.id < y.id ? -1 : x.id > y.id ? 1 : 0));
      return { data: { query: p.q, terms: t, results: hits.slice(0, limit) },
        meta: meta({ count: Math.min(hits.length, limit), total_matches: hits.length, filters: p,
          method: "BM25 over titles, questions, statements, materials and conditions; deterministic; no generative AI" }) };
    },
    rank: (p) => {
      const t = terms(p.q);
      const limit = has(p, "limit") ? p.limit : 7;
      const byStudy = new Map();
      for (const d of index.docs) {
        if (d.type !== "finding" && d.type !== "study") continue;
        const [s, matched] = scoreDoc(d, t, index);
        if (s <= 0) continue;
        if (!byStudy.has(d.study_id)) byStudy.set(d.study_id, { study_score: 0.0, findings: [], terms: new Set() });
        const e = byStudy.get(d.study_id);
        matched.forEach((m) => e.terms.add(m));
        if (d.type === "study") e.study_score = s;
        else e.findings.push({ id: d.id, title: d.title, evidence_type: d.evidence_type, score: round4(s), _raw: s });
      }
      const out = [];
      for (const [sid, e] of byStudy) {
        const fs = e.findings.sort((x, y) => (y._raw - x._raw) || (x.id < y.id ? -1 : x.id > y.id ? 1 : 0));
        let total = e.study_score;
        for (const f of fs.slice(0, 3)) total = total + f._raw;
        const st = studies[sid];
        out.push({ study_id: sid, name: st.name, score: round4(total), study_score: round4(e.study_score),
          independence_from_bass2: st.independence_from_bass2, lineage_group: st.lineage_group, data_in_service: st.data_in_service,
          matched_terms: [...e.terms].sort(), supporting_findings: fs.slice(0, 3).map((f) => pick(f, ["id", "title", "evidence_type", "score"])) });
      }
      out.sort((x, y) => (y.score - x.score) || (x.study_id < y.study_id ? -1 : x.study_id > y.study_id ? 1 : 0));
      return { data: { query: p.q, terms: t, results: out.slice(0, limit) },
        meta: meta({ count: Math.min(out.length, limit), filters: p,
          method: "Study score = BM25 score of the study record + the three best-matching findings of that study" }) };
    },
    bass2Summary: () => one(b.bass2.summary, { units: b.units,
      source: "Computed from NASA/TM-20210011385 Tables 5.1 and 7.1 and PSI-25 by ember/consistency.py" }),
    listTests: (p) => {
      const cfgOk = (t) => !has(p, "flow_configuration") || (p.flow_configuration === "unresolved" ? t.flow_configuration === null : t.flow_configuration === p.flow_configuration);
      const rows = b.bass2.tests.filter((t) => (!has(p, "pi") || t.pi === p.pi) && (!has(p, "fuel_family") || t.fuel_family === p.fuel_family)
        && cfgOk(t) && (!has(p, "flag") || t.flags.includes(p.flag)));
      return list(rows, p, { units: b.units, source: "NASA PSI-25 experimental table + NASA/TM-20210011385 Appendix A" });
    },
    getTest: (id) => {
      const t = get(tests, id, "BASS-II test");
      const steps = b.bass2.pmma_steps.filter((s) => s.test_id === id);
      const agg = b.bass2.pmma_tests.find((x) => x.test_id === id) || null;
      const fab = b.bass2.fabric_outcomes.find((x) => x.test_id === id) || null;
      const fnd = b.findings.filter((f) => f.test_ids.includes(id)).map(findingSummary);
      return one({ ...t, pmma_spread_steps: steps, pmma_test_aggregate: agg, fabric_outcome: fab, findings: fnd }, { units: b.units });
    },
    pmmaSteps: (p) => list(b.bass2.pmma_steps.filter((s) => (!has(p, "test_id") || s.test_id === p.test_id)
      && (!has(p, "thickness_mm") || feq(s.thickness_mm, p.thickness_mm)) && (!has(p, "width_cm") || feq(s.width_cm, p.width_cm))
      && (!has(p, "sides_burning") || s.sides_burning === p.sides_burning) && (!has(p, "tracked") || s.spread_rate_tracked === p.tracked)), p,
      { units: b.units, measurement_level: "repeated_step_within_test",
        warning: "Steps within a test are not independent; use /bass2/pmma/tests for test-level analysis.",
        source: "NASA/TM-20210011385 Table 5.1, p. 57" }),
    pmmaTests: (p) => list(b.bass2.pmma_tests.filter((t) => (!has(p, "thickness_mm") || feq(t.thickness_mm, p.thickness_mm))
      && (!has(p, "width_cm") || feq(t.width_cm, p.width_cm)) && (!has(p, "sides_burning") || t.sides_burning === p.sides_burning)), p,
      { units: b.units, measurement_level: "independent_test_run", source: "NASA/TM-20210011385 Table 5.1, p. 57 (aggregated per test)" }),
    fabricOutcomes: (p) => list(b.bass2.fabric_outcomes.filter((f) => (!has(p, "outcome_class") || f.outcome_class === p.outcome_class)
      && (!has(p, "sample_reused") || f.sample_reused === p.sample_reused) && (!has(p, "width_cm") || feq(f.sample_width_cm, p.width_cm))), p,
      { units: b.units, measurement_level: "independent_test_run",
        warning: "Quench flows are upper bounds; flow resolution +/-0.5 cm/s (p. 66).", source: "NASA/TM-20210011385 Table 7.1, p. 96" }),
  };

  const routes = [
    ["", h.root, {}],
    ["/health", h.health, {}],
    ["/meta", h.meta, {}],
    ["/studies", h.listStudies, { lineage: ["str", 40], independence: ["enum", INDEPENDENCE] }],
    ["/studies/{id}", h.getStudy, {}],
    ["/sources", h.listSources, { access: ["enum", ACCESS] }],
    ["/sources/{id}", h.getSource, {}],
    ["/findings", h.listFindings, { study: ["str", 40], topic: ["enum", TOPICS], evidence_type: ["enum", EVIDENCE_TYPES],
      independence: ["enum", INDEPENDENCE], lineage: ["str", 40], test_id: ["str", 20] }],
    ["/findings/{id}", h.getFinding, {}],
    ["/comparisons", h.listComparisons, { topic: ["enum", TOPICS] }],
    ["/comparisons/{id}", h.getComparison, {}],
    ["/gaps", h.listGaps, { status: ["enum", ["open", "partly_resolved", "resolved"]], priority: ["enum", ["high", "medium", "low"]], study: ["str", 40] }],
    ["/search", h.search, { q: ["str", 200], type: ["enum", SEARCH_TYPES], limit: ["int", 1, 50], evidence_type: ["enum", EVIDENCE_TYPES], study: ["str", 40] }],
    ["/rank/investigations", h.rank, { q: ["str", 200], limit: ["int", 1, 10] }],
    ["/consistency", h.consistency, { status: ["enum", ["pass", "fail"]] }],
    ["/bass2/summary", h.bass2Summary, {}],
    ["/bass2/tests", h.listTests, { pi: ["str", 40], fuel_family: ["str", 60], flow_configuration: ["enum", FLOW_CFG], flag: ["str", 60] }],
    ["/bass2/tests/{id}", h.getTest, {}],
    ["/bass2/pmma/steps", h.pmmaSteps, { test_id: ["str", 20], thickness_mm: ["num"], width_cm: ["num"], sides_burning: ["int", 1, 2], tracked: ["bool"] }],
    ["/bass2/pmma/tests", h.pmmaTests, { thickness_mm: ["num"], width_cm: ["num"], sides_burning: ["int", 1, 2] }],
    ["/bass2/fabric/outcomes", h.fabricOutcomes, { outcome_class: ["enum", OUTCOMES], sample_reused: ["bool"], width_cm: ["num"] }],
  ];
  const required = { "/search": ["q"], "/rank/investigations": ["q"] };

  function handle(method, path, pairs) {
    try {
      if (method !== "GET" && method !== "HEAD") throw new ApiError(405, "method_not_allowed", "Only GET is supported", { method });
      if (!path.startsWith(PREFIX) && path !== "/" && path !== "") throw new ApiError(404, "not_found", "No such endpoint", { path });
      let sub = path.startsWith(PREFIX) ? path.slice(PREFIX.length) : "";
      if (sub.length > 1 && sub.endsWith("/")) sub = sub.slice(0, -1);
      if (sub === "/") sub = "";
      for (const [pattern, fn, specs] of routes) {
        if (pattern.includes("{id}")) {
          const head = pattern.split("{id}")[0];
          const rest = sub.slice(head.length);
          if (sub.startsWith(head) && !rest.includes("/") && rest) {
            parseParams(pairs, specs);
            return [200, fn(rest)];
          }
        } else if (sub === pattern) {
          const params = parseParams(pairs, specs, required[pattern] || []);
          return [200, fn(params)];
        }
      }
      throw new ApiError(404, "not_found", "No such endpoint", { path });
    } catch (e) {
      if (e instanceof ApiError) return [e.status, errBody(e)];
      throw e;
    }
  }

  return { handle };
}
