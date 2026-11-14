# Methodology

How NASA data becomes served evidence, and the rules that keep it honest.

## 1. Pipeline

```
data/raw/*.csv ──► ember/ingest.py ──► ember/consistency.py ──► ember/build.py ──► data/build/evidence_bundle.json
data/curated/*.json ─────────────────────────┘                       │
                                                                     ├─► worker/ (Cloudflare Worker, production)
                                                                     └─► ember/api.py (FastAPI, local dev and tests)
```

`python -m ember.build` fails (exit 1) if any input fails validation or any consistency check fails. Nothing is served from an unchecked bundle.

## 2. Ingestion and validation (`ember/ingest.py`)

| Input | Origin | Validation |
| --- | --- | --- |
| `PSI-25_Experimental_table_BASS-II.csv` | NASA PSI-25 (DOI 10.60555/4qc4-de67) | SHA-256 must equal `71e792bf…c042`; exact 17-column header; 129 unique test ids |
| `bass2_pmma_spread_steps_clean.csv` | Table 5.1, p. 57 of NASA/TM-20210011385, verified in the validation notebook | Required columns; a tracked step must have a spread rate |
| `bass2_fabric_outcomes_clean.csv` | Table 7.1, p. 96 | Required columns; outcome must be one of four classes |
| `bass2_flow_configuration_verified.csv` | Appendix A, pp. 103–113, verified by three methods | Configuration must be Opposed, Concurrent, Stagnation or blank |

Rules: unparseable cells (`none`, `OR`, `>500`, `over`, blank) become `null` and raw text is kept; values are never imputed; suspect values are flagged, not corrected (for example a final O2 of 1.6 vol% is excluded from O2-consumed and flagged `o2_final_implausible`).

## 3. Repeated measurements versus independent tests

Table 5.1 lists 1–4 flow steps per test. Steps in one test share a sample, an oxygen history and stored heat, so they are not independent. The service keeps two levels:

- `/bass2/pmma/steps`: 41 steps, `measurement_level = repeated_step_within_test`.
- `/bass2/pmma/tests`: 18 tests, `measurement_level = independent_test_run`, aggregated as the mean (and geometric mean, min, max) of each test's tracked steps.

All test-level statistics use the second. The build recomputes the aggregates and checks them against the validation notebook's file.

## 4. Evidence model

**Evidence type**
- `verified_measurement`: a value checked against the NASA source table and PSI-25. Allowed only for BASS-II findings backed by a verified dataset (enforced).
- `author_conclusion`: stated by NASA or partner authors; the data behind it are not in this service. Includes author-reported numbers (for example Saffire spread rates, SoFIE-GEL case values).
- `hypothesis`: proposed or deduced by authors and not established by the cited work (for example the backdraft hazard, the low-flow extinction strategy).

**Independence and lineage.** Each study has a `lineage_group` (shared hardware and campaign) and an `independence_from_bass2` level. Papers on the same campaign (Link et al. 2018, Olson and Ferkul 2015, ICES-2015-196) are filed under BASS-II, so they can never count as replication. A comparison's `independent_experiment_count` is the number of distinct lineages among its findings, recomputed by the build.

**No numeric merging.** Every comparison has `numeric_merge_allowed = false` with a stated reason. BASS-II, Saffire and SoFIE-GEL differ in duct, scale, geometry, pressure and flow definition.

## 5. Statistics served

Computed in `ember/consistency.py` from the data, never typed in:

- Test-level Spearman rank correlation between thickness and mean spread rate (n = 18).
- Median of per-test mean spread by thickness.
- Count of multi-step tests where spread fell at every step, and where flow fell at every step.
- Fabric outcome counts, reused-sample count, lowest fresh-sample oxygen with a sustained flame.
- Through-origin slope of O2 consumed on CO2 produced (PSI-25), against PMMA stoichiometry (6:5 = 1.2).
- Olson rod test count reconciliation.

Bootstrap intervals and the random-intercept model are reported in finding text from the validation notebook; the notebook reproduces them. All statistics are descriptive. No predictive model is served.

## 6. Automated scientific consistency checks (51)

| Category | What is checked |
| --- | --- |
| ingestion | Row counts, unique ids, every Table 5.1 and 7.1 test exists in PSI-25, flow configuration unresolved only for the five known tests |
| traceability | O2 in Tables 5.1 and 7.1 equals PSI-25; fabric tests are SIBAL; Table 5.1 tests are opposed and Table 7.1 concurrent; every source reference resolves and has a locator; every BASS-II test id in a finding exists |
| units | Spread rate, velocity, oxygen, thickness and width within physical ranges; final O2 ≤ initial; quench final flow ≤ start; every reported value has a unit |
| repeated_measures | Aggregates match the notebook; 39 steps from 18 tests; level labels correct |
| reproduction | Numbers stated in findings F-B2-01, -02, -04, -05, -10 and F-OF15-01 are recomputed from data and must match |
| evidence_rules | Valid evidence types and topics; verified measurements only from verified BASS-II data; none rests on an abstract-only source; every finding has a limitation; the unsourced 0.88 mm/s value appears nowhere |
| cross_study | Comparisons reference known findings; independent-experiment count equals distinct lineages; numeric merging forbidden |

Negative tests in `tests/test_consistency.py` deliberately break each rule and confirm the check fails.

## 7. Retrieval

BM25 over findings, studies and comparisons (43 documents). Tokenizer: lowercase, split on non-alphanumerics (decimals kept), stopwords removed, synonym folding, light stemming. IDF is precomputed in Python and shipped in the bundle; the Worker applies the same arithmetic in the same order, so scores match exactly. Investigation ranking = study-record score + its three best finding scores. Every result returns `matched_terms` so the UI can explain a ranking.

## 8. Saffire-V review method

The ICES-2021-218 presentation was read slide by slide as rendered images. Values were taken only where printed (conditions on slide 3, geometry on slide 5, inlet flow and ignition time in frame overlays). Slides 7–9 (flame front, flame length, flicker) export with axes only; no values were digitized or estimated. Conclusions were classified individually; see `SAFFIRE_V_REVIEW.md`.
