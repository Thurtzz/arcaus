"""NASA data ingestion and validation."""
import shutil

import pytest

from ember import ingest


def test_psi25_loads_with_verified_hash():
    rows = ingest.load_psi25()
    assert len(rows) == 129
    assert len({r["test_id"] for r in rows}) == 129


def test_psi25_hash_mismatch_is_rejected(tmp_path, monkeypatch):
    src = ingest.RAW / ingest.PSI25_FILE
    dst = tmp_path / ingest.PSI25_FILE
    dst.write_bytes(src.read_bytes().replace(b"22.2", b"22.3", 1))
    for p in ingest.RAW.glob("*.csv"):
        if p.name != ingest.PSI25_FILE:
            shutil.copy(p, tmp_path / p.name)
    monkeypatch.setattr(ingest, "RAW", tmp_path)
    with pytest.raises(ingest.IngestError, match="hash"):
        ingest.load_psi25()


def test_missing_values_stay_missing():
    t = {r["test_id"]: r for r in ingest.load_psi25()}
    assert t["B2"]["co2_final_vol_pct"] is None            # blank cell
    assert t["O4"]["co_final_ppm"] is None                 # "OR" (over range)
    assert "co_final_over_range" in t["O4"]["flags"]
    assert t["B2"]["o2_consumed_vol_pct"] is None          # implausible final O2 1.6 is excluded, not corrected
    assert "o2_final_implausible" in t["B2"]["flags"]


def test_date_flags_distinguish_typos_from_2016_tests():
    t = {r["test_id"]: r for r in ingest.load_psi25()}
    assert "date_year_likely_typo" in t["T9"]["flags"]
    assert "run_feb_2016_not_in_appendix_a" in t["O20"]["flags"]


def test_units_parsed_from_free_text():
    t = {r["test_id"]: r for r in ingest.load_psi25()}
    assert t["O4"]["rod_diameter_mm"] == pytest.approx(9.525)
    assert t["B1"]["thickness_mm"] == pytest.approx(0.1)
    assert t["M11"]["width_cm"] == 1


def test_repeated_steps_aggregate_to_independent_tests():
    data = ingest.load_all()
    steps = [s for s in data["bass2_pmma_steps"] if s["spread_rate_tracked"]]
    assert len(steps) == 39
    assert len(data["bass2_pmma_tests"]) == 18
    m8 = next(t for t in data["bass2_pmma_tests"] if t["test_id"] == "M8")
    assert m8["n_steps"] == 3 and m8["velocities_cm_s"] == [10, 6, 5]
    assert m8["measurement_level"] == "independent_test_run"
    assert {s["test_id"] for s in data["bass2_pmma_steps"] if not s["spread_rate_tracked"]} == {"M6", "M12"}


def test_fabric_flags():
    f = {r["test_id"]: r for r in ingest.load_fabric_outcomes()}
    assert len(f) == 27
    assert "o2_reading_flagged_by_nasa" in f["T1"]["flags"]
    assert f["T18"]["quench_note"] and f["T4"]["final_flow_is_upper_bound"]
    assert sum(r["sample_reused"] for r in f.values()) == 8


def test_bad_outcome_class_rejected(tmp_path, monkeypatch):
    for p in ingest.RAW.glob("*.csv"):
        shutil.copy(p, tmp_path / p.name)
    path = tmp_path / "bass2_fabric_outcomes_clean.csv"
    path.write_text(path.read_text().replace("quenched (low flow)", "probably quenched", 1))
    monkeypatch.setattr(ingest, "RAW", tmp_path)
    with pytest.raises(ingest.IngestError, match="unknown outcome"):
        ingest.load_fabric_outcomes()
