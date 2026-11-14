"""Build the evidence bundle served by both the FastAPI app and the Cloudflare Worker.

    python -m ember.build            # validate, run checks, write data/build/
    python -m ember.build --check    # validate and run checks only

Exit code 1 if ingestion fails or any consistency check fails.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import consistency, ingest, search

ROOT = Path(__file__).resolve().parent.parent
CURATED = ROOT / "data" / "curated"
BUILD = ROOT / "data" / "build"
BUNDLE_VERSION = "1.0.0"
API_VERSION = "v1"

EVIDENCE_LABELS = {
    "verified_measurement": "Verified measurement",
    "author_conclusion": "Author conclusion",
    "hypothesis": "Hypothesis",
}

UNITS = {
    "spread_rate": "mm/s", "velocity": "cm/s", "flow": "cm/s", "o2": "vol% (calibrated, by volume)", "co2": "vol%",
    "co": "ppm", "thickness": "mm", "width": "cm", "rod_diameter": "mm", "burn_time": "min", "gmt_day": "day of year (GMT)",
}


def load_curated() -> dict:
    out = {}
    for name, key in (("sources", "sources"), ("studies", "studies"), ("findings", "findings"),
                      ("comparisons", "comparisons"), ("data_gaps", "gaps")):
        doc = json.loads((CURATED / f"{name}.json").read_text())
        out[key] = doc[key]
        if name == "studies":
            out["independence_levels"] = doc["independence_levels"]
    out["hashes"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(CURATED.glob("*.json"))}
    return out


def enrich(curated: dict) -> None:
    studies = {s["id"]: s for s in curated["studies"]}
    for f in curated["findings"]:
        st = studies[f["study_id"]]
        f["study_name"] = st["name"]
        f["lineage_group"] = st["lineage_group"]
        f["independence_from_bass2"] = st["independence_from_bass2"]
        f["evidence_type_label"] = EVIDENCE_LABELS[f["evidence_type"]]
        f["counts_as_replication_of_bass2"] = st["independence_from_bass2"] in ("separate_experiment_shared_team", "separate_investigation")
    by_study = {}
    for f in curated["findings"]:
        by_study.setdefault(f["study_id"], []).append(f["id"])
    for s in curated["studies"]:
        s["finding_ids"] = by_study.get(s["id"], [])
    fmap = {f["id"]: f for f in curated["findings"]}
    for c in curated["comparisons"]:
        c["studies"] = sorted({fmap[i]["study_id"] for i in c["finding_ids"]})
        c["lineage_groups"] = sorted({fmap[i]["lineage_group"] for i in c["finding_ids"]})


def build(write: bool = True) -> dict:
    data = ingest.load_all()
    curated = load_curated()
    stats = consistency.computed_statistics(data)
    checks = consistency.run_checks(data, curated, stats)
    enrich(curated)
    index = search.build_index(curated["findings"], curated["studies"], curated["comparisons"])
    failed = [c for c in checks if c["status"] != "pass"]
    content = {
        "studies": curated["studies"], "sources": curated["sources"], "findings": curated["findings"],
        "comparisons": curated["comparisons"], "gaps": curated["gaps"],
        "independence_levels": curated["independence_levels"], "evidence_labels": EVIDENCE_LABELS, "units": UNITS,
        "bass2": {
            "tests": data["bass2_tests"], "pmma_steps": data["bass2_pmma_steps"],
            "pmma_tests": data["bass2_pmma_tests"], "fabric_outcomes": data["bass2_fabric_outcomes"],
            "summary": stats,
        },
        "consistency": {"checks": checks, "passed": len(checks) - len(failed), "failed": len(failed)},
        "search_index": index,
    }
    digest = hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()
    bundle = {
        "manifest": {
            "bundle_version": BUNDLE_VERSION, "api_version": API_VERSION, "content_sha256": digest,
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "input_hashes": data["input_hashes"], "curated_hashes": curated["hashes"],
            "counts": {"studies": len(curated["studies"]), "sources": len(curated["sources"]),
                       "findings": len(curated["findings"]), "comparisons": len(curated["comparisons"]),
                       "gaps": len(curated["gaps"]), "bass2_tests": len(data["bass2_tests"]),
                       "bass2_pmma_steps": len(data["bass2_pmma_steps"]), "bass2_pmma_tests": len(data["bass2_pmma_tests"]),
                       "bass2_fabric_outcomes": len(data["bass2_fabric_outcomes"]), "search_docs": index["n_docs"]},
            "authoritative_reference": "NASA/TM-20210011385 (BASS-II Summary Report)",
        },
        **content,
    }
    if write:
        BUILD.mkdir(parents=True, exist_ok=True)
        (BUILD / "evidence_bundle.json").write_text(json.dumps(bundle, indent=1, ensure_ascii=False, allow_nan=False))
        for name, rows in (("findings", curated["findings"]), ("comparisons", curated["comparisons"]),
                           ("studies", curated["studies"]), ("sources", curated["sources"]), ("gaps", curated["gaps"])):
            (BUILD / f"{name}.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))
        (BUILD / "consistency_report.json").write_text(json.dumps(bundle["consistency"], indent=1))
    return bundle


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="validate and run checks without writing")
    args = ap.parse_args(argv)
    try:
        bundle = build(write=not args.check)
    except ingest.IngestError as e:
        print(f"INGEST FAILED: {e}", file=sys.stderr)
        return 1
    cons = bundle["consistency"]
    for c in cons["checks"]:
        mark = "PASS" if c["status"] == "pass" else "FAIL"
        print(f"[{mark}] {c['id']:10s} {c['description']}" + (f"  ({c['detail']})" if c["detail"] and mark == "FAIL" else ""))
    print(f"\n{cons['passed']} passed, {cons['failed']} failed; {bundle['manifest']['counts']}")
    return 0 if cons["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
