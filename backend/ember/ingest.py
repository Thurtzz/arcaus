"""NASA data ingestion and validation for the BASS-II datasets.

Every loader checks the file against an expected schema and returns plain
records (list of dicts) with typed values. Missing or unparseable values become
None; raw text is kept alongside parsed values. Nothing is imputed.
"""
from __future__ import annotations

import csv
import hashlib
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

PSI25_FILE = "PSI-25_Experimental_table_BASS-II.csv"
PSI25_SHA256 = "71e792bf6b5fb5ea620c5dd70fbbac05515992e12aefcf5dff47312caa48c042"
PSI25_COLUMNS = [
    "PI", "Test #", "Date", "GMT", "Sample #", "Fuel Sample Material", "Flow restrictor",
    "Fan display", "Air display", "Radiometer gain (1000 250 50 10)", "Total Frames Shot",
    "Calibrated initial O2 % by vol", "Calibrated final O2 % by vol", "Initial CO2 % by vol",
    "Final CO2 % by vol", "Initial CO (ppm)", "Final CO (ppm)",
]

SOURCE_TABLE_5_1 = "NASA/TM-20210011385 Table 5.1, p. 57"
SOURCE_TABLE_7_1 = "NASA/TM-20210011385 Table 7.1, p. 96"
SOURCE_APPENDIX_A = "NASA/TM-20210011385 Appendix A, pp. 103-113"
SOURCE_PSI25 = "NASA PSI-25 experimental table (DOI 10.60555/4qc4-de67)"


class IngestError(ValueError):
    """Raised when an input file fails validation."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _num(text):
    if text is None:
        return None
    s = str(text).strip()
    if s == "":
        return None
    try:
        v = float(s)
    except ValueError:
        return None
    return None if math.isnan(v) else v


def _bool(text):
    s = str(text).strip().lower()
    if s in ("true", "1", "yes"):
        return True
    if s in ("false", "0", "no"):
        return False
    if s == "":
        return None
    raise IngestError(f"not a boolean: {text!r}")


def _clean(text) -> str:
    return " ".join(str(text if text is not None else "").split())


def _read_csv(name: str, encoding: str = "utf-8") -> tuple[list[str], list[dict]]:
    path = RAW / name
    if not path.exists():
        raise IngestError(f"missing input file: {name}")
    with path.open(encoding=encoding, newline="") as fh:
        reader = csv.DictReader(fh)
        header = [_clean(h) for h in (reader.fieldnames or [])]
        rows = []
        for raw in reader:
            rows.append({_clean(k): v for k, v in raw.items()})
    return header, rows


def _require(header: list[str], required: list[str], name: str):
    missing = [c for c in required if c not in header]
    if missing:
        raise IngestError(f"{name}: missing columns {missing}")


# --------------------------------------------------------------------------- PSI-25

def _fuel_family(s: str) -> str:
    t = s.lower()
    if "rod" in t:
        return "PMMA rod"
    if "spher" in t:
        return "PMMA spherical section"
    if "sibal" in t:
        return "SIBAL fabric"
    if "nomex" in t:
        return "Nomex"
    if "wax" in t or "candle" in t:
        return "wax candle"
    return "PMMA flat (film/sheet/slab)"


def _rod_diameter_mm(s: str):
    if "rod" not in s.lower():
        return None
    m = re.search(r'(\d+/\d+|\d*\.\d+)\s*"', s)
    if not m:
        return None
    v = m.group(1)
    inch = float(v.split("/")[0]) / float(v.split("/")[1]) if "/" in v else float(v)
    return round(inch * 25.4, 3)


def _thickness_mm(s: str):
    t = s.lower()
    if "rod" in t:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*micron", t)
    if m:
        return float(m.group(1)) / 1000
    m = re.search(r"(\d+(?:\.\d+)?)\s*mm", t)
    return float(m.group(1)) if m else None


def _width_cm(s: str):
    t = s.lower()
    if "rod" in t or "spher" in t:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*cm", t)
    return float(m.group(1)) if m else None


def load_psi25(check_hash: bool = True) -> list[dict]:
    path = RAW / PSI25_FILE
    if check_hash and sha256(path) != PSI25_SHA256:
        raise IngestError("PSI-25 table hash does not match the verified copy")
    header, rows = _read_csv(PSI25_FILE, encoding="utf-8-sig")
    if header != PSI25_COLUMNS:
        raise IngestError(f"PSI-25 columns changed: {header}")
    out = []
    seen = set()
    for r in rows:
        tid = _clean(r["Test #"])
        if not tid or tid in seen:
            raise IngestError(f"PSI-25: empty or duplicate test id {tid!r}")
        seen.add(tid)
        fuel = _clean(r["Fuel Sample Material"])
        o2i, o2f = _num(r["Calibrated initial O2 % by vol"]), _num(r["Calibrated final O2 % by vol"])
        co2i, co2f = _num(r["Initial CO2 % by vol"]), _num(r["Final CO2 % by vol"])
        coi, cof = _num(r["Initial CO (ppm)"]), _num(r["Final CO (ppm)"])
        date_raw = _clean(r["Date"])
        flags = []
        o2_final_suspect = o2f is not None and o2i is not None and (o2f > o2i + 0.3 or o2f < o2i - 5)
        if o2_final_suspect:
            flags.append("o2_final_implausible")
        if date_raw.endswith("2018"):
            flags.append("date_year_likely_typo")
        if date_raw.endswith("2016"):
            flags.append("run_feb_2016_not_in_appendix_a")
        for col, label in (("Calibrated final O2 % by vol", "o2_final"), ("Final CO2 % by vol", "co2_final"), ("Final CO (ppm)", "co_final")):
            raw = _clean(r[col]).lower()
            if raw in ("or", "over") or raw.startswith(">"):
                flags.append(f"{label}_over_range")
        d_o2 = None if (o2_final_suspect or o2i is None or o2f is None) else round(o2i - o2f, 3)
        out.append({
            "test_id": tid,
            "pi": _clean(r["PI"]),
            "date_raw": date_raw,
            "gmt_day": _num(r["GMT"]),
            "sample_id": _clean(r["Sample #"]),
            "fuel_raw": fuel,
            "fuel_family": _fuel_family(fuel),
            "rod_diameter_mm": _rod_diameter_mm(fuel),
            "thickness_mm": _thickness_mm(fuel),
            "width_cm": _width_cm(fuel),
            "flow_restrictors": _num(r["Flow restrictor"]),
            "fan_display_raw": _clean(r["Fan display"]),
            "air_display_raw": _clean(r["Air display"]),
            "air_single_value_cm_s": _num(r["Air display"]),
            "o2_initial_vol_pct": o2i,
            "o2_final_vol_pct": o2f,
            "co2_initial_vol_pct": co2i,
            "co2_final_vol_pct": co2f,
            "co_initial_ppm": coi,
            "co_final_ppm": cof,
            "o2_consumed_vol_pct": d_o2,
            "co2_produced_vol_pct": None if (co2i is None or co2f is None) else round(co2f - co2i, 3),
            "co_produced_ppm": None if (coi is None or cof is None) else round(cof - coi, 3),
            "flags": flags,
            "source": SOURCE_PSI25,
        })
    if len(out) != 129:
        raise IngestError(f"PSI-25 expected 129 rows, found {len(out)}")
    return out


# ------------------------------------------------------------- Appendix A flow config

FLOW_CONFIGS = {"Opposed", "Concurrent", "Stagnation"}


def load_flow_configuration() -> dict[str, dict]:
    header, rows = _read_csv("bass2_flow_configuration_verified.csv")
    _require(header, ["test_id", "pi", "printed_page", "value_printed_in_appendix", "flow_configuration", "verification", "observations_machine_extracted"], "flow configuration")
    out = {}
    for r in rows:
        cfg = _clean(r["flow_configuration"])
        if cfg and cfg not in FLOW_CONFIGS:
            raise IngestError(f"unknown flow configuration {cfg!r} for {r['test_id']}")
        page = _num(r["printed_page"])
        out[_clean(r["test_id"])] = {
            "flow_configuration": cfg or None,
            "value_printed_in_appendix": _clean(r["value_printed_in_appendix"]) or None,
            "flow_configuration_verification": _clean(r["verification"]),
            "appendix_printed_page": int(page) if page is not None else None,
            "appendix_observation_machine_extracted": _clean(r["observations_machine_extracted"]) or None,
        }
    return out


# ----------------------------------------------------------------- Table 5.1 (PMMA)

def load_pmma_steps() -> list[dict]:
    cols = ["test_id", "thickness_mm", "width_cm", "sides_burning", "step_order", "velocity_cm_s", "spread_rate_mm_s",
            "note", "burn_time_min", "o2_initial", "o2_final", "flow_configuration", "o2_mid", "n_steps_in_test", "spread_rate_tracked"]
    header, rows = _read_csv("bass2_pmma_spread_steps_clean.csv")
    _require(header, cols, "Table 5.1 steps")
    out = []
    for r in rows:
        tracked = _bool(r["spread_rate_tracked"])
        spread = _num(r["spread_rate_mm_s"])
        if tracked and spread is None:
            raise IngestError(f"Table 5.1 {r['test_id']}: tracked step without a spread rate")
        out.append({
            "test_id": _clean(r["test_id"]),
            "step_order": int(_num(r["step_order"])),
            "thickness_mm": _num(r["thickness_mm"]),
            "width_cm": _num(r["width_cm"]),
            "sides_burning": int(_num(r["sides_burning"])),
            "velocity_cm_s": _num(r["velocity_cm_s"]),
            "spread_rate_mm_s": spread,
            "spread_rate_tracked": tracked,
            "note": _clean(r["note"]) or None,
            "burn_time_min": _num(r["burn_time_min"]),
            "o2_initial_vol_pct": _num(r["o2_initial"]),
            "o2_final_vol_pct": _num(r["o2_final"]),
            "o2_mid_vol_pct": _num(r["o2_mid"]),
            "n_steps_in_test": int(_num(r["n_steps_in_test"])) if _num(r["n_steps_in_test"]) is not None else 0,
            "flow_configuration": _clean(r["flow_configuration"]),
            "measurement_level": "repeated_step_within_test",
            "source": SOURCE_TABLE_5_1,
        })
    return out


def aggregate_pmma_tests(steps: list[dict]) -> list[dict]:
    """One record per independent test run, from its tracked flow steps."""
    by = {}
    for s in steps:
        if s["spread_rate_tracked"]:
            by.setdefault(s["test_id"], []).append(s)
    out = []
    for tid, g in by.items():
        g = sorted(g, key=lambda s: s["step_order"])
        rates = [s["spread_rate_mm_s"] for s in g]
        vel = [s["velocity_cm_s"] for s in g]
        f = g[0]
        out.append({
            "test_id": tid,
            "thickness_mm": f["thickness_mm"],
            "width_cm": f["width_cm"],
            "sides_burning": f["sides_burning"],
            "n_steps": len(g),
            "spread_mean_mm_s": round(sum(rates) / len(rates), 4),
            "spread_geomean_mm_s": round(math.exp(sum(math.log(x) for x in rates) / len(rates)), 4),
            "spread_min_mm_s": min(rates),
            "spread_max_mm_s": max(rates),
            "velocity_min_cm_s": min(vel),
            "velocity_max_cm_s": max(vel),
            "velocities_cm_s": vel,
            "spread_rates_mm_s": rates,
            "o2_initial_vol_pct": f["o2_initial_vol_pct"],
            "o2_final_vol_pct": f["o2_final_vol_pct"],
            "o2_mid_vol_pct": f["o2_mid_vol_pct"],
            "burn_time_min": f["burn_time_min"],
            "flow_configuration": f["flow_configuration"],
            "measurement_level": "independent_test_run",
            "aggregation": "mean of the test's tracked flow steps",
            "source": SOURCE_TABLE_5_1,
        })
    return sorted(out, key=lambda r: (r["thickness_mm"], r["test_id"]))


def load_pmma_tests_reference() -> list[dict]:
    """The per-test file produced by the validation notebook, used to cross-check aggregation."""
    header, rows = _read_csv("bass2_pmma_spread_by_test.csv")
    _require(header, ["test_id", "n_steps", "spread_mean", "spread_min", "spread_max"], "Table 5.1 by-test")
    return [{"test_id": r["test_id"], "n_steps": int(_num(r["n_steps"])), "spread_mean": _num(r["spread_mean"]),
             "spread_min": _num(r["spread_min"]), "spread_max": _num(r["spread_max"])} for r in rows]


# --------------------------------------------------------------- Table 7.1 (fabric)

OUTCOME_CLASSES = {"quenched (low flow)", "blow-off (high flow)", "burned, no extinction limit reached", "no ignition"}


def load_fabric_outcomes() -> list[dict]:
    cols = ["test_id", "sample_width_cm", "flow_cm_s_text", "flow_start_cm_s", "flow_final_cm_s", "flow_was_changed", "o2_vol_pct",
            "comment", "outcome_class", "sample_reused", "o2_flagged_by_nasa", "quench_note", "flow_configuration",
            "psi_air_display_raw", "appendix_observation_machine_extracted"]
    header, rows = _read_csv("bass2_fabric_outcomes_clean.csv")
    _require(header, cols, "Table 7.1")
    out = []
    for r in rows:
        oc = _clean(r["outcome_class"])
        if oc not in OUTCOME_CLASSES:
            raise IngestError(f"Table 7.1 {r['test_id']}: unknown outcome {oc!r}")
        flags = []
        if _bool(r["sample_reused"]):
            flags.append("sample_reused")
        if _bool(r["o2_flagged_by_nasa"]):
            flags.append("o2_reading_flagged_by_nasa")
        if _clean(r["quench_note"]):
            flags.append("quench_note")
        out.append({
            "test_id": _clean(r["test_id"]),
            "sample_width_cm": _num(r["sample_width_cm"]),
            "flow_cm_s_text": _clean(r["flow_cm_s_text"]),
            "flow_start_cm_s": _num(r["flow_start_cm_s"]),
            "flow_final_cm_s": _num(r["flow_final_cm_s"]),
            "flow_was_changed": _bool(r["flow_was_changed"]),
            "o2_vol_pct": _num(r["o2_vol_pct"]),
            "nasa_comment": _clean(r["comment"]) or None,
            "outcome_class": oc,
            "sample_reused": _bool(r["sample_reused"]),
            "o2_flagged_by_nasa": _bool(r["o2_flagged_by_nasa"]),
            "quench_note": _clean(r["quench_note"]) or None,
            "flow_configuration": _clean(r["flow_configuration"]),
            "psi_air_display_raw": _clean(r["psi_air_display_raw"]),
            "appendix_observation_machine_extracted": _clean(r["appendix_observation_machine_extracted"]) or None,
            "final_flow_is_upper_bound": oc.startswith("quenched"),
            "flags": flags,
            "measurement_level": "independent_test_run",
            "source": SOURCE_TABLE_7_1,
        })
    return out


def load_all(check_hash: bool = True) -> dict:
    tests = load_psi25(check_hash=check_hash)
    cfg = load_flow_configuration()
    for t in tests:
        c = cfg.get(t["test_id"])
        if c is None:
            raise IngestError(f"flow configuration missing for {t['test_id']}")
        t.update(c)
    steps = load_pmma_steps()
    return {
        "bass2_tests": tests,
        "bass2_pmma_steps": steps,
        "bass2_pmma_tests": aggregate_pmma_tests(steps),
        "bass2_pmma_tests_reference": load_pmma_tests_reference(),
        "bass2_fabric_outcomes": load_fabric_outcomes(),
        "input_hashes": {p.name: sha256(p) for p in sorted(RAW.glob("*.csv"))},
    }
