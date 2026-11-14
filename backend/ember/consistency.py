"""Automated scientific consistency checks.

Each check returns a dict {id, category, description, status, detail}. The build
fails if any check fails. Checks recompute numbers from data rather than trusting
the curated text, and enforce the evidence rules (no verified measurement without
a verified dataset, no replication counted within one experiment lineage).
"""
from __future__ import annotations

import re
from statistics import median

from scipy.stats import spearmanr

TEST_ID_RE = re.compile(r"^[BFMOPT]\d+[ab]?$")
EVIDENCE_TYPES = {"verified_measurement", "author_conclusion", "hypothesis"}
INDEPENDENCE = {"same_experiment", "same_lineage", "separate_experiment_shared_team", "separate_investigation"}
TOPICS = {"airflow", "oxygen", "geometry", "extinction_mechanism", "ventilation_change", "combustion_products",
          "ignition", "materials", "detection", "dataset_scope"}
VERIFIED_DATASETS = {"bass2_tests", "bass2_pmma_steps", "bass2_pmma_tests", "bass2_fabric_outcomes"}


def computed_statistics(data: dict) -> dict:
    tests = data["bass2_pmma_tests"]
    steps = [s for s in data["bass2_pmma_steps"] if s["spread_rate_tracked"]]
    rho, p = spearmanr([t["thickness_mm"] for t in tests], [t["spread_mean_mm_s"] for t in tests])
    by_thick = {}
    for t in tests:
        by_thick.setdefault(t["thickness_mm"], []).append(t["spread_mean_mm_s"])
    seq = []
    for t in tests:
        if t["n_steps"] > 1:
            r, v = t["spread_rates_mm_s"], t["velocities_cm_s"]
            seq.append({"test_id": t["test_id"],
                        "spread_falls_every_step": all(b < a for a, b in zip(r, r[1:])),
                        "flow_down_every_step": all(b < a for a, b in zip(v, v[1:]))})
    fab = data["bass2_fabric_outcomes"]
    counts = {}
    for f in fab:
        counts[f["outcome_class"]] = counts.get(f["outcome_class"], 0) + 1
    fresh_burn = [f["o2_vol_pct"] for f in fab if not f["sample_reused"] and f["outcome_class"] != "no ignition"]
    fresh_noign = sorted(f["o2_vol_pct"] for f in fab if not f["sample_reused"] and f["outcome_class"] == "no ignition")

    def slope(family):
        rows = [t for t in data["bass2_tests"] if t["fuel_family"] == family
                and t["o2_consumed_vol_pct"] is not None and t["co2_produced_vol_pct"] is not None]
        num = sum(t["o2_consumed_vol_pct"] * t["co2_produced_vol_pct"] for t in rows)
        den = sum(t["co2_produced_vol_pct"] ** 2 for t in rows)
        return round(num / den, 3), len(rows)

    s_rod, n_rod = slope("PMMA rod")
    s_flat, n_flat = slope("PMMA flat (film/sheet/slab)")
    olson = [t for t in data["bass2_tests"] if t["pi"] == "Olson"]
    return {
        "pmma_tests_with_spread": len(tests),
        "pmma_spread_steps": len(steps),
        "pmma_untracked_tests": sorted({s["test_id"] for s in data["bass2_pmma_steps"] if not s["spread_rate_tracked"]}),
        "steps_per_test": {str(k): sum(1 for t in tests if t["n_steps"] == k) for k in sorted({t["n_steps"] for t in tests})},
        "thickness_vs_spread_spearman_rho_test_level": round(float(rho), 3),
        "thickness_vs_spread_spearman_p_test_level": round(float(p), 4),
        "median_test_mean_spread_by_thickness_mm_s": {str(k): round(median(v), 4) for k, v in sorted(by_thick.items())},
        "tests_by_thickness": {str(k): len(v) for k, v in sorted(by_thick.items())},
        "multi_step_tests": len(seq),
        "multi_step_tests_spread_falls_every_step": sum(1 for s in seq if s["spread_falls_every_step"]),
        "multi_step_tests_flow_down_every_step": sum(1 for s in seq if s["flow_down_every_step"]),
        "fabric_tests": len(fab),
        "fabric_outcome_counts": dict(sorted(counts.items())),
        "fabric_reused_samples": sum(1 for f in fab if f["sample_reused"]),
        "fabric_lowest_o2_sustained_flame_fresh": min(fresh_burn),
        "fabric_no_ignition_o2_fresh": fresh_noign,
        "stoichiometric_slope_pmma_rod": s_rod, "stoichiometric_slope_pmma_rod_n": n_rod,
        "stoichiometric_slope_pmma_flat": s_flat, "stoichiometric_slope_pmma_flat_n": n_flat,
        "olson_rod_tests": len(olson),
        "olson_rod_tests_feb_2016": sum(1 for t in olson if "run_feb_2016_not_in_appendix_a" in t["flags"]),
        "statistics_note": "Descriptive statistics on investigator-chosen test conditions. Not predictive.",
    }


def run_checks(data: dict, curated: dict, stats: dict) -> list[dict]:
    results = []

    def check(cid, category, description, ok, detail=""):
        results.append({"id": cid, "category": category, "description": description,
                        "status": "pass" if ok else "fail", "detail": detail})

    tests = {t["test_id"]: t for t in data["bass2_tests"]}
    steps = data["bass2_pmma_steps"]
    fab = data["bass2_fabric_outcomes"]
    studies = {s["id"]: s for s in curated["studies"]}
    sources = {s["id"]: s for s in curated["sources"]}
    findings = {f["id"]: f for f in curated["findings"]}

    # ---- ingestion and data integrity
    check("DATA-01", "ingestion", "PSI-25 has 129 unique tests", len(tests) == 129, f"{len(tests)} tests")
    bad = [s["test_id"] for s in steps if s["test_id"] not in tests]
    check("DATA-02", "ingestion", "Every Table 5.1 test exists in PSI-25", not bad, ", ".join(bad))
    bad = [s["test_id"] for s in steps if abs(s["o2_initial_vol_pct"] - tests[s["test_id"]]["o2_initial_vol_pct"]) > 1e-9
           or abs(s["o2_final_vol_pct"] - tests[s["test_id"]]["o2_final_vol_pct"]) > 1e-9]
    check("DATA-03", "traceability", "Table 5.1 initial and final O2 equal PSI-25 values", not bad, ", ".join(sorted(set(bad))))
    bad = [f["test_id"] for f in fab if f["test_id"] not in tests or abs(f["o2_vol_pct"] - tests[f["test_id"]]["o2_initial_vol_pct"]) > 0.051]
    check("DATA-04", "traceability", "Table 7.1 O2 within 0.05 vol% of PSI-25 initial O2", not bad, ", ".join(bad))
    bad = [f["test_id"] for f in fab if tests[f["test_id"]]["fuel_family"] != "SIBAL fabric"]
    check("DATA-05", "traceability", "Table 7.1 tests are SIBAL fabric in PSI-25", not bad, ", ".join(bad))
    bad = sorted({s["test_id"] for s in steps if tests[s["test_id"]]["flow_configuration"] != "Opposed"})
    check("DATA-06", "traceability", "All Table 5.1 tests are opposed flow in Appendix A", not bad, ", ".join(bad))
    bad = [f["test_id"] for f in fab if tests[f["test_id"]]["flow_configuration"] != "Concurrent"]
    check("DATA-07", "traceability", "All Table 7.1 tests are concurrent flow in Appendix A", not bad, ", ".join(bad))
    unresolved = sorted(t for t, r in tests.items() if not r["flow_configuration"])
    check("DATA-08", "ingestion", "Flow configuration unresolved only for O1, O2, O20, O21, O22",
          unresolved == ["O1", "O2", "O20", "O21", "O22"], ", ".join(unresolved))

    # ---- units and physical ranges
    tracked = [s for s in steps if s["spread_rate_tracked"]]
    check("UNIT-01", "units", "PMMA spread rates in (0, 1) mm/s", all(0 < s["spread_rate_mm_s"] < 1 for s in tracked))
    check("UNIT-02", "units", "Opposed flow velocities in (0, 60] cm/s", all(0 < s["velocity_cm_s"] <= 60 for s in steps))
    check("UNIT-03", "units", "O2 values within 10-25 vol%",
          all(10 <= s["o2_initial_vol_pct"] <= 25 and 10 <= s["o2_final_vol_pct"] <= 25 for s in steps)
          and all(10 <= f["o2_vol_pct"] <= 25 for f in fab))
    check("UNIT-04", "units", "PMMA thickness in 1-5 mm, width 1.2 or 2.2 cm",
          all(s["thickness_mm"] in (1, 2, 3, 4, 5) and s["width_cm"] in (1.2, 2.2) for s in steps))
    check("UNIT-05", "units", "Final O2 never exceeds initial O2 in Table 5.1",
          all(s["o2_final_vol_pct"] <= s["o2_initial_vol_pct"] for s in steps))
    check("UNIT-06", "units", "Quench final flow lies below start flow",
          all(f["flow_final_cm_s"] <= f["flow_start_cm_s"] for f in fab if f["outcome_class"].startswith("quenched")))

    # ---- repeated measurements vs independent tests
    ref = {r["test_id"]: r for r in data["bass2_pmma_tests_reference"]}
    agg = {t["test_id"]: t for t in data["bass2_pmma_tests"]}
    bad = [t for t in agg if t not in ref or ref[t]["n_steps"] != agg[t]["n_steps"]
           or abs(ref[t]["spread_mean"] - agg[t]["spread_mean_mm_s"]) > 1e-4
           or ref[t]["spread_min"] != agg[t]["spread_min_mm_s"] or ref[t]["spread_max"] != agg[t]["spread_max_mm_s"]]
    check("REP-01", "repeated_measures", "Per-test aggregates recomputed from steps match the validation notebook",
          not bad and set(ref) == set(agg), ", ".join(bad))
    check("REP-02", "repeated_measures", "39 tracked steps from 18 independent tests",
          stats["pmma_spread_steps"] == 39 and stats["pmma_tests_with_spread"] == 18,
          f"{stats['pmma_spread_steps']} steps, {stats['pmma_tests_with_spread']} tests")
    check("REP-03", "repeated_measures", "Steps are labelled repeated, tests independent",
          all(s["measurement_level"] == "repeated_step_within_test" for s in steps)
          and all(t["measurement_level"] == "independent_test_run" for t in data["bass2_pmma_tests"]))

    # ---- findings reproduce from data
    f01 = next(v for v in findings["F-B2-01"]["reported_values"] if v["quantity"].startswith("test-level Spearman"))
    check("SCI-01", "reproduction", "F-B2-01 test-level rho reproduces from data",
          abs(f01["value"] - stats["thickness_vs_spread_spearman_rho_test_level"]) <= 0.001,
          f"stated {f01['value']}, computed {stats['thickness_vs_spread_spearman_rho_test_level']}")
    check("SCI-02", "reproduction", "F-B2-02 spread fell at every step in all multi-step tests (13 of 13; flow down in 12)",
          stats["multi_step_tests"] == 13 and stats["multi_step_tests_spread_falls_every_step"] == 13
          and stats["multi_step_tests_flow_down_every_step"] == 12,
          f"{stats['multi_step_tests_spread_falls_every_step']} of {stats['multi_step_tests']}; flow down {stats['multi_step_tests_flow_down_every_step']}")
    c = stats["fabric_outcome_counts"]
    check("SCI-03", "reproduction", "F-B2-04 fabric outcome counts 6/1/6/14 reproduce",
          c == {"blow-off (high flow)": 1, "burned, no extinction limit reached": 14, "no ignition": 6, "quenched (low flow)": 6}, str(c))
    check("SCI-04", "reproduction", "F-B2-05 lowest fresh-sample sustained-flame O2 is 16.9 vol%; no ignition at 16.4, 16.4, 16.8",
          stats["fabric_lowest_o2_sustained_flame_fresh"] == 16.9 and stats["fabric_no_ignition_o2_fresh"] == [16.4, 16.4, 16.8])
    check("SCI-05", "reproduction", "F-B2-10 O2:CO2 slopes reproduce near PMMA stoichiometry (1.2)",
          abs(stats["stoichiometric_slope_pmma_rod"] - 1.23) <= 0.01 and abs(stats["stoichiometric_slope_pmma_flat"] - 1.20) <= 0.01,
          f"rod {stats['stoichiometric_slope_pmma_rod']}, flat {stats['stoichiometric_slope_pmma_flat']}")
    check("SCI-06", "reproduction", "F-OF15-01 Olson rod count reconciles: 27 tests minus 3 run in Feb 2016 equals 24",
          stats["olson_rod_tests"] == 27 and stats["olson_rod_tests_feb_2016"] == 3)
    m = stats["median_test_mean_spread_by_thickness_mm_s"]
    vals = {v["quantity"]: v["value"] for v in findings["F-B2-01"]["reported_values"]}
    check("SCI-07", "reproduction", "F-B2-01 per-test median spread at 1 mm and 5 mm reproduces",
          abs(vals["median of per-test mean spread, 1 mm"] - m["1.0"]) < 1e-4 and abs(vals["median of per-test mean spread, 5 mm"] - m["5.0"]) < 1e-4, str(m))

    # ---- evidence rules
    bad = [f["id"] for f in findings.values() if f["evidence_type"] not in EVIDENCE_TYPES]
    check("EVD-01", "evidence_rules", "Every finding has a valid evidence type", not bad, ", ".join(bad))
    bad = [f["id"] for f in findings.values() if f["evidence_type"] == "verified_measurement"
           and (f["study_id"] != "BASS-II" or not f["datasets"] or not set(f["datasets"]) <= VERIFIED_DATASETS)]
    check("EVD-02", "evidence_rules", "Verified measurements come only from verified BASS-II datasets", not bad, ", ".join(bad))
    bad = [f["id"] for f in findings.values() if f["evidence_type"] == "verified_measurement"
           and all(sources[r["source_id"]]["access"] in ("abstract_only",) for r in f["source_refs"])]
    check("EVD-03", "evidence_rules", "No verified measurement rests on an abstract-only source", not bad, ", ".join(bad))
    bad = [f["id"] for f in findings.values() if f["study_id"] not in studies]
    check("EVD-04", "traceability", "Every finding names a known study", not bad, ", ".join(bad))
    bad = [f"{f['id']}:{r['source_id']}" for f in findings.values() for r in f["source_refs"]
           if r["source_id"] not in sources or not r.get("locator")]
    check("EVD-05", "traceability", "Every source reference resolves and has a page, table, figure or slide locator", not bad, ", ".join(bad))
    bad = [f"{f['id']}:{t}" for f in findings.values() if f["study_id"] in ("BASS-II",) for t in f["test_ids"]
           if TEST_ID_RE.match(t) and t not in tests]
    check("EVD-06", "traceability", "Every BASS-II test identifier in a finding exists in PSI-25", not bad, ", ".join(bad))
    bad = [f["id"] for f in findings.values() if not set(f["topics"]) <= TOPICS or not f["topics"]]
    check("EVD-07", "evidence_rules", "Finding topics come from the controlled list", not bad, ", ".join(bad))
    bad = [f"{f['id']}:{v['quantity']}" for f in findings.values() for v in f["reported_values"] if not v.get("unit")]
    check("EVD-08", "units", "Every reported value carries a unit", not bad, ", ".join(bad))
    bad = [f["id"] for f in findings.values() if not f["limitations"]]
    check("EVD-09", "evidence_rules", "Every finding states at least one limitation", not bad, ", ".join(bad))
    bad = [s["id"] for s in studies.values() if s["independence_from_bass2"] not in INDEPENDENCE]
    check("EVD-10", "evidence_rules", "Every study has a valid independence level", not bad, ", ".join(bad))
    excluded = [f["id"] for f in findings.values() if "0.88" in f["statement"] or any("0.88" in str(v["value"]) for v in f["reported_values"])]
    check("EVD-11", "evidence_rules", "The unsourced 0.88 mm/s Saffire-V value appears in no finding", not excluded, ", ".join(excluded))

    # ---- cross-study rules
    for cmp in curated["comparisons"]:
        missing = [fid for fid in cmp["finding_ids"] if fid not in findings]
        lineages = {studies[findings[fid]["study_id"]]["lineage_group"] for fid in cmp["finding_ids"] if fid in findings}
        check(f"CMP-{cmp['id'][-2:]}-A", "cross_study", f"{cmp['id']} references only known findings", not missing, ", ".join(missing))
        check(f"CMP-{cmp['id'][-2:]}-B", "cross_study",
              f"{cmp['id']} independent experiment count equals distinct lineages ({len(lineages)})",
              cmp["independent_experiment_count"] == len(lineages), f"declared {cmp['independent_experiment_count']}, lineages {sorted(lineages)}")
        check(f"CMP-{cmp['id'][-2:]}-C", "cross_study", f"{cmp['id']} forbids numeric merging", cmp["numeric_merge_allowed"] is False)
    bad = [g["id"] for g in curated["gaps"] for fid in g["related_findings"] if fid not in findings]
    check("GAP-01", "traceability", "Data gaps reference known findings", not bad, ", ".join(bad))
    return results
