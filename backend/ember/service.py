"""Framework-free API logic. FastAPI (ember/api.py) wraps it; worker/src/service.js
is a line-for-line port. tests/test_parity.py proves both return identical bodies.

handle(method, path, query_pairs) -> (status_code, body_dict)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import search

ROOT = Path(__file__).resolve().parent.parent
BUNDLE_PATH = ROOT / "data" / "build" / "evidence_bundle.json"
PREFIX = "/api/v1"

EVIDENCE_TYPES = ["verified_measurement", "author_conclusion", "hypothesis"]
INDEPENDENCE = ["same_experiment", "same_lineage", "separate_experiment_shared_team", "separate_investigation"]
TOPICS = ["airflow", "oxygen", "geometry", "extinction_mechanism", "ventilation_change", "combustion_products",
          "ignition", "materials", "detection", "dataset_scope"]
OUTCOMES = ["quenched (low flow)", "blow-off (high flow)", "burned, no extinction limit reached", "no ignition"]
FLOW_CFG = ["Opposed", "Concurrent", "Stagnation", "unresolved"]
ACCESS = ["full_text", "full_text_extraction", "abstract_only", "dataset"]
SEARCH_TYPES = ["all", "finding", "study", "comparison"]


class ApiError(Exception):
    def __init__(self, status, code, message, details=None):
        super().__init__(message)
        self.status, self.code, self.message, self.details = status, code, message, details or {}


def err_body(e: ApiError) -> dict:
    return {"error": {"code": e.code, "message": e.message, "details": e.details}}


# ------------------------------------------------------------------- params

def _parse(name, raw, spec):
    kind = spec[0]
    if kind == "str":
        v = raw.strip()
        if not v or len(v) > spec[1]:
            raise ApiError(400, "invalid_parameter", f"'{name}' must be 1-{spec[1]} characters", {"parameter": name})
        return v
    if kind == "enum":
        if raw not in spec[1]:
            raise ApiError(400, "invalid_parameter", f"'{name}' must be one of the allowed values",
                           {"parameter": name, "allowed": spec[1]})
        return raw
    if kind == "int":
        if not re.fullmatch(r"-?\d+", raw):
            raise ApiError(400, "invalid_parameter", f"'{name}' must be an integer", {"parameter": name})
        v = int(raw)
        if v < spec[1] or v > spec[2]:
            raise ApiError(400, "invalid_parameter", f"'{name}' must be between {spec[1]} and {spec[2]}",
                           {"parameter": name, "min": spec[1], "max": spec[2]})
        return v
    if kind == "num":
        if not re.fullmatch(r"-?\d+(\.\d+)?", raw):
            raise ApiError(400, "invalid_parameter", f"'{name}' must be a number", {"parameter": name})
        return float(raw)
    if kind == "bool":
        if raw not in ("true", "false"):
            raise ApiError(400, "invalid_parameter", f"'{name}' must be 'true' or 'false'", {"parameter": name})
        return raw == "true"
    raise ValueError(kind)


def parse_params(pairs, specs: dict, required=()) -> dict:
    seen = {}
    for k, v in pairs:
        if k not in specs:
            raise ApiError(400, "unknown_parameter", f"Unknown query parameter '{k}'",
                           {"parameter": k, "allowed": sorted(specs)})
        if k in seen:
            raise ApiError(400, "duplicate_parameter", f"Query parameter '{k}' given more than once", {"parameter": k})
        seen[k] = v
    for r in required:
        if r not in seen:
            raise ApiError(400, "missing_parameter", f"Query parameter '{r}' is required", {"parameter": r})
    return {k: _parse(k, v, specs[k]) for k, v in seen.items()}


def _feq(a, b):
    return a is not None and abs(a - b) < 1e-9


# ------------------------------------------------------------------- service

class Service:
    def __init__(self, bundle: dict):
        self.b = bundle
        self.studies = {s["id"]: s for s in bundle["studies"]}
        self.sources = {s["id"]: s for s in bundle["sources"]}
        self.findings = {f["id"]: f for f in bundle["findings"]}
        self.comparisons = {c["id"]: c for c in bundle["comparisons"]}
        self.gaps = {g["id"]: g for g in bundle["gaps"]}
        self.tests = {t["test_id"]: t for t in bundle["bass2"]["tests"]}
        self.index = bundle["search_index"]
        self.routes = [
            ("", self.root, {}),
            ("/health", self.health, {}),
            ("/meta", self.meta, {}),
            ("/studies", self.list_studies, {"lineage": ("str", 40), "independence": ("enum", INDEPENDENCE)}),
            ("/studies/{id}", self.get_study, {}),
            ("/sources", self.list_sources, {"access": ("enum", ACCESS)}),
            ("/sources/{id}", self.get_source, {}),
            ("/findings", self.list_findings, {"study": ("str", 40), "topic": ("enum", TOPICS), "evidence_type": ("enum", EVIDENCE_TYPES),
                                               "independence": ("enum", INDEPENDENCE), "lineage": ("str", 40), "test_id": ("str", 20)}),
            ("/findings/{id}", self.get_finding, {}),
            ("/comparisons", self.list_comparisons, {"topic": ("enum", TOPICS)}),
            ("/comparisons/{id}", self.get_comparison, {}),
            ("/gaps", self.list_gaps, {"status": ("enum", ["open", "partly_resolved", "resolved"]),
                                       "priority": ("enum", ["high", "medium", "low"]), "study": ("str", 40)}),
            ("/search", self.search, {"q": ("str", 200), "type": ("enum", SEARCH_TYPES), "limit": ("int", 1, 50),
                                      "evidence_type": ("enum", EVIDENCE_TYPES), "study": ("str", 40)}),
            ("/rank/investigations", self.rank_investigations, {"q": ("str", 200), "limit": ("int", 1, 10)}),
            ("/consistency", self.consistency, {"status": ("enum", ["pass", "fail"])}),
            ("/bass2/summary", self.bass2_summary, {}),
            ("/bass2/tests", self.list_tests, {"pi": ("str", 40), "fuel_family": ("str", 60), "flow_configuration": ("enum", FLOW_CFG),
                                               "flag": ("str", 60)}),
            ("/bass2/tests/{id}", self.get_test, {}),
            ("/bass2/pmma/steps", self.pmma_steps, {"test_id": ("str", 20), "thickness_mm": ("num",), "width_cm": ("num",),
                                                     "sides_burning": ("int", 1, 2), "tracked": ("bool",)}),
            ("/bass2/pmma/tests", self.pmma_tests, {"thickness_mm": ("num",), "width_cm": ("num",), "sides_burning": ("int", 1, 2)}),
            ("/bass2/fabric/outcomes", self.fabric_outcomes, {"outcome_class": ("enum", OUTCOMES), "sample_reused": ("bool",),
                                                               "width_cm": ("num",)}),
        ]
        self.required = {"/search": ("q",), "/rank/investigations": ("q",)}

    # -------------------------------------------------------------- dispatch
    def handle(self, method: str, path: str, pairs):
        try:
            if method not in ("GET", "HEAD"):
                raise ApiError(405, "method_not_allowed", "Only GET is supported", {"method": method})
            if not path.startswith(PREFIX) and path not in ("/", ""):
                raise ApiError(404, "not_found", "No such endpoint", {"path": path})
            sub = path[len(PREFIX):] if path.startswith(PREFIX) else ""
            if len(sub) > 1 and sub.endswith("/"):
                sub = sub[:-1]
            if sub == "/":
                sub = ""
            for pattern, fn, specs in self.routes:
                if "{id}" in pattern:
                    head = pattern.split("{id}")[0]
                    if sub.startswith(head) and "/" not in sub[len(head):] and sub[len(head):]:
                        params = parse_params(pairs, specs)
                        return 200, fn(sub[len(head):], params)
                elif sub == pattern:
                    params = parse_params(pairs, specs, self.required.get(pattern, ()))
                    return 200, fn(params)
            raise ApiError(404, "not_found", "No such endpoint", {"path": path})
        except ApiError as e:
            return e.status, err_body(e)

    # -------------------------------------------------------------- helpers
    def _meta(self, extra=None):
        m = {"bundle_version": self.b["manifest"]["bundle_version"], "content_sha256": self.b["manifest"]["content_sha256"]}
        if extra:
            m.update(extra)
        return m

    def _list(self, rows, params, extra=None):
        meta = {"count": len(rows), "filters": params}
        if extra:
            meta.update(extra)
        return {"data": rows, "meta": self._meta(meta)}

    def _one(self, rec, extra=None):
        return {"data": rec, "meta": self._meta(extra)}

    def _get(self, table, key, kind):
        if key not in table:
            raise ApiError(404, "not_found", f"No {kind} with id '{key}'", {"id": key})
        return table[key]

    # -------------------------------------------------------------- endpoints
    def root(self, params):
        return self._one({"service": "EMBER / ORBIT evidence service", "api_version": "v1",
                          "endpoints": [PREFIX + p for p, _, _ in self.routes if p]})

    def health(self, params):
        c = self.b["consistency"]
        return self._one({"status": "ok" if c["failed"] == 0 else "degraded", "checks_passed": c["passed"],
                          "checks_failed": c["failed"], "generated_at": self.b["manifest"]["generated_at"]})

    def meta(self, params):
        return self._one({**self.b["manifest"], "units": self.b["units"], "evidence_labels": self.b["evidence_labels"],
                          "independence_levels": self.b["independence_levels"]})

    def list_studies(self, p):
        rows = [s for s in self.b["studies"]
                if ("lineage" not in p or s["lineage_group"] == p["lineage"])
                and ("independence" not in p or s["independence_from_bass2"] == p["independence"])]
        return self._list(rows, p)

    def get_study(self, sid, p):
        s = self._get(self.studies, sid, "study")
        return self._one({**s, "sources": [self.sources[x] for x in s["source_ids"]],
                          "findings": [self._finding_summary(self.findings[f]) for f in s["finding_ids"]]})

    def list_sources(self, p):
        rows = [s for s in self.b["sources"] if "access" not in p or s["access"] == p["access"]]
        return self._list(rows, p)

    def get_source(self, sid, p):
        s = self._get(self.sources, sid, "source")
        cited = [f["id"] for f in self.b["findings"] if any(r["source_id"] == sid for r in f["source_refs"])]
        return self._one({**s, "cited_by_findings": cited})

    def _finding_summary(self, f):
        return {k: f[k] for k in ("id", "title", "study_id", "evidence_type", "evidence_type_label", "independence_from_bass2", "topics")}

    def list_findings(self, p):
        rows = [f for f in self.b["findings"]
                if ("study" not in p or f["study_id"] == p["study"])
                and ("topic" not in p or p["topic"] in f["topics"])
                and ("evidence_type" not in p or f["evidence_type"] == p["evidence_type"])
                and ("independence" not in p or f["independence_from_bass2"] == p["independence"])
                and ("lineage" not in p or f["lineage_group"] == p["lineage"])
                and ("test_id" not in p or p["test_id"] in f["test_ids"])]
        return self._list(rows, p)

    def get_finding(self, fid, p):
        f = self._get(self.findings, fid, "finding")
        refs = [{**r, "source": self.sources[r["source_id"]]} for r in f["source_refs"]]
        st = self.studies[f["study_id"]]
        return self._one({**f, "source_refs": refs,
                          "study": {k: st[k] for k in ("id", "name", "platform", "lineage_group", "independence_from_bass2", "data_in_service")},
                          "comparisons": [c["id"] for c in self.b["comparisons"] if fid in c["finding_ids"]],
                          "gaps": [g["id"] for g in self.b["gaps"] if fid in g["related_findings"]]})

    def list_comparisons(self, p):
        rows = [c for c in self.b["comparisons"] if "topic" not in p or c["topic"] == p["topic"]]
        return self._list(rows, p)

    def get_comparison(self, cid, p):
        c = self._get(self.comparisons, cid, "comparison")
        rows = []
        for fid in c["finding_ids"]:
            f = self.findings[fid]
            rows.append({"finding_id": fid, "study_id": f["study_id"], "study_name": f["study_name"],
                         "lineage_group": f["lineage_group"], "independence_from_bass2": f["independence_from_bass2"],
                         "evidence_type": f["evidence_type"], "title": f["title"], "statement": f["statement"],
                         "material": f["material"], "geometry": f["geometry"], "conditions": f["conditions"],
                         "source_refs": f["source_refs"]})
        return self._one({**c, "rows": rows})

    def list_gaps(self, p):
        rows = [g for g in self.b["gaps"] if ("status" not in p or g["status"] == p["status"])
                and ("priority" not in p or g["priority"] == p["priority"])
                and ("study" not in p or g["study_id"] == p["study"])]
        return self._list(rows, p)

    def consistency(self, p):
        c = self.b["consistency"]
        rows = [x for x in c["checks"] if "status" not in p or x["status"] == p["status"]]
        return self._list(rows, p, {"passed": c["passed"], "failed": c["failed"]})

    # -------------------------------------------------------------- retrieval
    def _terms(self, q):
        terms = search.query_terms(q)
        if not terms:
            raise ApiError(400, "invalid_parameter", "'q' has no searchable terms after removing stopwords", {"parameter": "q"})
        return terms

    def search(self, p):
        terms = self._terms(p["q"])
        typ, limit = p.get("type", "all"), p.get("limit", 10)
        hits = []
        for d in self.index["docs"]:
            if typ != "all" and d["type"] != typ:
                continue
            if "evidence_type" in p and d["evidence_type"] != p["evidence_type"]:
                continue
            if "study" in p and d["study_id"] != p["study"]:
                continue
            s, matched = search.score_doc(d, terms, self.index)
            if s > 0:
                hits.append({"id": d["id"], "type": d["type"], "title": d["title"], "study_id": d["study_id"],
                             "evidence_type": d["evidence_type"], "score": search.round4(s), "matched_terms": matched})
        hits.sort(key=lambda h: (-h["score"], h["id"]))
        return {"data": {"query": p["q"], "terms": terms, "results": hits[:limit]},
                "meta": self._meta({"count": min(len(hits), limit), "total_matches": len(hits), "filters": p,
                                    "method": "BM25 over titles, questions, statements, materials and conditions; deterministic; no generative AI"})}

    def rank_investigations(self, p):
        terms = self._terms(p["q"])
        limit = p.get("limit", 7)
        by_study = {}
        for d in self.index["docs"]:
            if d["type"] not in ("finding", "study"):
                continue
            s, matched = search.score_doc(d, terms, self.index)
            if s <= 0:
                continue
            e = by_study.setdefault(d["study_id"], {"study_score": 0.0, "findings": [], "terms": set()})
            e["terms"].update(matched)
            if d["type"] == "study":
                e["study_score"] = s
            else:
                e["findings"].append({"id": d["id"], "title": d["title"], "evidence_type": d["evidence_type"], "score": search.round4(s), "_raw": s})
        out = []
        for sid, e in by_study.items():
            fs = sorted(e["findings"], key=lambda f: (-f["_raw"], f["id"]))
            total = e["study_score"]
            for f in fs[:3]:
                total = total + f["_raw"]
            st = self.studies[sid]
            out.append({"study_id": sid, "name": st["name"], "score": search.round4(total),
                        "study_score": search.round4(e["study_score"]), "independence_from_bass2": st["independence_from_bass2"],
                        "lineage_group": st["lineage_group"], "data_in_service": st["data_in_service"],
                        "matched_terms": sorted(e["terms"]),
                        "supporting_findings": [{k: f[k] for k in ("id", "title", "evidence_type", "score")} for f in fs[:3]]})
        out.sort(key=lambda r: (-r["score"], r["study_id"]))
        return {"data": {"query": p["q"], "terms": terms, "results": out[:limit]},
                "meta": self._meta({"count": min(len(out), limit), "filters": p,
                                    "method": "Study score = BM25 score of the study record + the three best-matching findings of that study"})}

    # -------------------------------------------------------------- BASS-II data
    def bass2_summary(self, p):
        return self._one(self.b["bass2"]["summary"], {"units": self.b["units"],
                         "source": "Computed from NASA/TM-20210011385 Tables 5.1 and 7.1 and PSI-25 by ember/consistency.py"})

    def list_tests(self, p):
        def cfg_ok(t):
            if "flow_configuration" not in p:
                return True
            if p["flow_configuration"] == "unresolved":
                return t["flow_configuration"] is None
            return t["flow_configuration"] == p["flow_configuration"]
        rows = [t for t in self.b["bass2"]["tests"]
                if ("pi" not in p or t["pi"] == p["pi"]) and ("fuel_family" not in p or t["fuel_family"] == p["fuel_family"])
                and cfg_ok(t) and ("flag" not in p or p["flag"] in t["flags"])]
        return self._list(rows, p, {"units": self.b["units"], "source": "NASA PSI-25 experimental table + NASA/TM-20210011385 Appendix A"})

    def get_test(self, tid, p):
        t = self._get(self.tests, tid, "BASS-II test")
        steps = [s for s in self.b["bass2"]["pmma_steps"] if s["test_id"] == tid]
        agg = next((x for x in self.b["bass2"]["pmma_tests"] if x["test_id"] == tid), None)
        fab = next((x for x in self.b["bass2"]["fabric_outcomes"] if x["test_id"] == tid), None)
        fnd = [self._finding_summary(f) for f in self.b["findings"] if tid in f["test_ids"]]
        return self._one({**t, "pmma_spread_steps": steps, "pmma_test_aggregate": agg, "fabric_outcome": fab, "findings": fnd},
                         {"units": self.b["units"]})

    def pmma_steps(self, p):
        rows = [s for s in self.b["bass2"]["pmma_steps"]
                if ("test_id" not in p or s["test_id"] == p["test_id"])
                and ("thickness_mm" not in p or _feq(s["thickness_mm"], p["thickness_mm"]))
                and ("width_cm" not in p or _feq(s["width_cm"], p["width_cm"]))
                and ("sides_burning" not in p or s["sides_burning"] == p["sides_burning"])
                and ("tracked" not in p or s["spread_rate_tracked"] == p["tracked"])]
        return self._list(rows, p, {"units": self.b["units"], "measurement_level": "repeated_step_within_test",
                                    "warning": "Steps within a test are not independent; use /bass2/pmma/tests for test-level analysis.",
                                    "source": "NASA/TM-20210011385 Table 5.1, p. 57"})

    def pmma_tests(self, p):
        rows = [t for t in self.b["bass2"]["pmma_tests"]
                if ("thickness_mm" not in p or _feq(t["thickness_mm"], p["thickness_mm"]))
                and ("width_cm" not in p or _feq(t["width_cm"], p["width_cm"]))
                and ("sides_burning" not in p or t["sides_burning"] == p["sides_burning"])]
        return self._list(rows, p, {"units": self.b["units"], "measurement_level": "independent_test_run",
                                    "source": "NASA/TM-20210011385 Table 5.1, p. 57 (aggregated per test)"})

    def fabric_outcomes(self, p):
        rows = [f for f in self.b["bass2"]["fabric_outcomes"]
                if ("outcome_class" not in p or f["outcome_class"] == p["outcome_class"])
                and ("sample_reused" not in p or f["sample_reused"] == p["sample_reused"])
                and ("width_cm" not in p or _feq(f["sample_width_cm"], p["width_cm"]))]
        return self._list(rows, p, {"units": self.b["units"], "measurement_level": "independent_test_run",
                                    "warning": "Quench flows are upper bounds; flow resolution +/-0.5 cm/s (p. 66).",
                                    "source": "NASA/TM-20210011385 Table 7.1, p. 96"})


_SERVICE = None


def get_service() -> Service:
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = Service(json.loads(BUNDLE_PATH.read_text()))
    return _SERVICE
