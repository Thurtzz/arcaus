"""Automated scientific consistency checks."""
import copy

from ember import consistency, ingest
from ember.build import load_curated


def _run(curated=None):
    data = ingest.load_all()
    cur = curated or load_curated()
    stats = consistency.computed_statistics(data)
    return {c["id"]: c for c in consistency.run_checks(data, cur, stats)}, stats


def test_all_checks_pass(bundle):
    failed = [c for c in bundle["consistency"]["checks"] if c["status"] != "pass"]
    assert not failed, failed
    assert bundle["consistency"]["passed"] >= 50


def test_statistics_reproduce():
    _, s = _run()
    assert s["thickness_vs_spread_spearman_rho_test_level"] == -0.718
    assert s["multi_step_tests_spread_falls_every_step"] == 13
    assert s["fabric_outcome_counts"]["quenched (low flow)"] == 6
    assert s["olson_rod_tests"] - s["olson_rod_tests_feb_2016"] == 24


def test_check_catches_wrong_stated_value():
    cur = load_curated()
    bad = copy.deepcopy(cur)
    f = next(x for x in bad["findings"] if x["id"] == "F-B2-01")
    f["reported_values"][0]["value"] = -0.9
    checks, _ = _run(bad)
    assert checks["SCI-01"]["status"] == "fail"


def test_check_blocks_verified_measurement_outside_bass2():
    bad = copy.deepcopy(load_curated())
    f = next(x for x in bad["findings"] if x["id"] == "F-S5-01")
    f["evidence_type"] = "verified_measurement"
    checks, _ = _run(bad)
    assert checks["EVD-02"]["status"] == "fail"


def test_check_blocks_counting_same_experiment_as_replication():
    bad = copy.deepcopy(load_curated())
    c = next(x for x in bad["comparisons"] if x["id"] == "CMP-04")
    c["independent_experiment_count"] = 3
    checks, _ = _run(bad)
    assert checks["CMP-04-B"]["status"] == "fail"


def test_check_blocks_numeric_merge():
    bad = copy.deepcopy(load_curated())
    bad["comparisons"][0]["numeric_merge_allowed"] = True
    checks, _ = _run(bad)
    assert checks["CMP-01-C"]["status"] == "fail"


def test_check_blocks_unsourced_saffire_value():
    bad = copy.deepcopy(load_curated())
    f = next(x for x in bad["findings"] if x["id"] == "F-S5-01")
    f["reported_values"].append({"quantity": "rib edge speed", "value": 0.88, "unit": "mm/s", "note": ""})
    checks, _ = _run(bad)
    assert checks["EVD-11"]["status"] == "fail"


def test_check_catches_unknown_test_id():
    bad = copy.deepcopy(load_curated())
    next(x for x in bad["findings"] if x["id"] == "F-B2-04")["test_ids"].append("T99")
    checks, _ = _run(bad)
    assert checks["EVD-06"]["status"] == "fail"
