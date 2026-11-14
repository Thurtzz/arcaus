# API contract — EMBER / ORBIT evidence service, v1

Base path `/api/v1`. All endpoints are `GET` (also `HEAD`; `OPTIONS` returns 204 for CORS preflight). Responses are JSON. The Cloudflare Worker and the FastAPI app return byte-for-byte equivalent bodies; this is tested on 79 request cases in Node and in Cloudflare's own runtime.

## Response envelope

Success:

```json
{ "data": <object or array>, "meta": { "bundle_version": "1.0.0", "content_sha256": "…", "count": 3, "filters": { … }, … } }
```

`meta.content_sha256` identifies the exact evidence bundle; show it in the UI footer or log it with screenshots. List endpoints add `count` and `filters` (the parsed, applied filters). BASS-II data endpoints add `units`, `measurement_level`, `source` and sometimes a `warning` the UI should display.

Error:

```json
{ "error": { "code": "invalid_parameter", "message": "'limit' must be between 1 and 50", "details": { "parameter": "limit", "min": 1, "max": 50 } } }
```

| HTTP | `code` | When |
| --- | --- | --- |
| 400 | `unknown_parameter` | A query parameter the endpoint does not accept (`details.allowed` lists valid ones) |
| 400 | `duplicate_parameter` | The same parameter twice |
| 400 | `missing_parameter` | `q` missing on `/search` or `/rank/investigations` |
| 400 | `invalid_parameter` | Wrong type, out of range, not in the allowed set (`details.allowed`), or a query with no searchable terms |
| 404 | `not_found` | Unknown endpoint or id |
| 405 | `method_not_allowed` | Anything other than GET/HEAD/OPTIONS |
| 500 | `internal_error` | Unexpected failure (Worker only) |

Parameter types: `str` (1–N chars, trimmed), `enum` (exact match), `int` (digits only, range-checked), `num` (decimal, no exponent), `bool` (`true` or `false` only). Successful responses are cacheable for 300 s; errors are `no-store`.

## Service

| Endpoint | Parameters | Returns |
| --- | --- | --- |
| `/api/v1` | — | Endpoint list |
| `/api/v1/health` | — | `status` (`ok` or `degraded`), `checks_passed`, `checks_failed`, `generated_at` |
| `/api/v1/meta` | — | Manifest: versions, input and curated file SHA-256, record counts, `units`, `evidence_labels`, `independence_levels` |
| `/api/v1/consistency` | `status` = pass\|fail | The automated scientific consistency checks and their results |

## Evidence

| Endpoint | Parameters | Returns |
| --- | --- | --- |
| `/api/v1/studies` | `lineage` (e.g. `BASS`, `Saffire`), `independence` | Investigations with lineage and independence from BASS-II |
| `/api/v1/studies/{id}` | — | Study plus its sources and finding summaries. Ids: `BASS-II`, `BASS`, `SAFFIRE-I-III`, `SAFFIRE-IV-V`, `SOFIE-GEL`, `FLEX`, `SAME-R` |
| `/api/v1/sources` | `access` = full_text\|full_text_extraction\|abstract_only\|dataset | Every cited document with URL and what was actually read |
| `/api/v1/sources/{id}` | — | Source plus `cited_by_findings` |
| `/api/v1/findings` | `study`, `topic`, `evidence_type`, `independence`, `lineage`, `test_id` | Findings (full records) |
| `/api/v1/findings/{id}` | — | Finding with expanded `source_refs[].source`, `study`, related `comparisons` and `gaps` |
| `/api/v1/comparisons` | `topic` | Cross-study comparison cards |
| `/api/v1/comparisons/{id}` | — | Card plus `rows`: one per finding with study, independence, evidence type, conditions and sources |
| `/api/v1/gaps` | `status` = open\|partly_resolved\|resolved, `priority` = high\|medium\|low, `study` | Unresolved data gaps |

Enumerations:
- `evidence_type`: `verified_measurement`, `author_conclusion`, `hypothesis`
- `independence`: `same_experiment`, `same_lineage`, `separate_experiment_shared_team`, `separate_investigation`
- `topic`: `airflow`, `oxygen`, `geometry`, `extinction_mechanism`, `ventilation_change`, `combustion_products`, `ignition`, `materials`, `detection`, `dataset_scope`

### Finding record (key fields)

| Field | Meaning |
| --- | --- |
| `id`, `title`, `research_question`, `topics` | Identification |
| `study_id`, `study_name`, `lineage_group`, `independence_from_bass2`, `counts_as_replication_of_bass2` | Investigation and lineage; `counts_as_replication_of_bass2` is false for the same experiment or lineage |
| `test_ids` | Experiment or test identifiers (PSI-25 ids for BASS-II; Saffire and SoFIE-GEL case ids as published) |
| `material`, `geometry`, `conditions` (`flow_direction`, `flow_cm_s`, `o2_vol_pct`, `pressure`) | Experimental context, as text ranges |
| `statement`, `reported_values[]` (`quantity`, `value`, `unit`, `note`) | The finding |
| `evidence_type`, `evidence_type_label`, `evidence_basis` | Evidence classification and why |
| `limitations[]`, `implications[]` | Uncertainty and research implications |
| `source_refs[]` (`source_id`, `locator`) | Page, table, figure or slide |
| `datasets[]` | Service datasets that back a verified measurement |

### Comparison record (key fields)

`question`, `agreement`, `differences`, `independent_experiment_count` (distinct lineages, recomputed by the build), `independence_note`, `numeric_merge_allowed` (always `false`), `numeric_merge_reason`, `implications`, `limitations`, `studies`, `lineage_groups`, `finding_ids`.

## Retrieval and ranking

| Endpoint | Parameters | Returns |
| --- | --- | --- |
| `/api/v1/search` | `q` (required, ≤ 200 chars), `type` = all\|finding\|study\|comparison, `limit` 1–50 (default 10), `evidence_type`, `study` | `data.terms` (normalized query terms), `data.results[]` with `id`, `type`, `title`, `study_id`, `evidence_type`, `score`, `matched_terms`; `meta.total_matches` |
| `/api/v1/rank/investigations` | `q` (required), `limit` 1–10 (default 7) | Investigations ranked for a research question, each with `score`, `study_score`, `independence_from_bass2`, `data_in_service`, `matched_terms` and up to three `supporting_findings` |

Ranking is BM25 (k1 = 1.2, b = 0.75) over titles, questions, statements, materials and conditions, with synonym folding (acrylic/Plexiglas → pmma, O2 → oxygen, ventilation/fan → airflow, extinguish → extinction) and light stemming. It is deterministic and explainable through `matched_terms`. No generative model is involved.

## BASS-II data

| Endpoint | Parameters | Returns |
| --- | --- | --- |
| `/api/v1/bass2/summary` | — | Verified statistics computed at build (test-level rho, medians by thickness, step counts, fabric outcome counts, stoichiometric slopes) |
| `/api/v1/bass2/tests` | `pi`, `fuel_family`, `flow_configuration` = Opposed\|Concurrent\|Stagnation\|unresolved, `flag` | All 129 PSI-25 tests with parsed conditions, gas readings, flow configuration, `flags` |
| `/api/v1/bass2/tests/{test_id}` | — | One test plus its PMMA steps, PMMA test aggregate, fabric outcome and findings |
| `/api/v1/bass2/pmma/steps` | `test_id`, `thickness_mm`, `width_cm`, `sides_burning` 1\|2, `tracked` | 41 flow steps (39 tracked). `measurement_level` = `repeated_step_within_test` |
| `/api/v1/bass2/pmma/tests` | `thickness_mm`, `width_cm`, `sides_burning` | 18 independent tests, aggregated from their steps. `measurement_level` = `independent_test_run` |
| `/api/v1/bass2/fabric/outcomes` | `outcome_class`, `sample_reused`, `width_cm` | 27 fabric tests with outcome, flow sweep and flags |

`fuel_family` values: `PMMA rod`, `PMMA flat (film/sheet/slab)`, `PMMA spherical section`, `SIBAL fabric`, `Nomex`, `wax candle`.
`outcome_class` values: `quenched (low flow)`, `blow-off (high flow)`, `burned, no extinction limit reached`, `no ignition`.
Test `flags`: `o2_final_implausible`, `date_year_likely_typo`, `run_feb_2016_not_in_appendix_a`, `o2_final_over_range`, `co2_final_over_range`, `co_final_over_range`. Fabric `flags`: `sample_reused`, `o2_reading_flagged_by_nasa`, `quench_note`.

Units (also in every BASS-II response under `meta.units`): spread rate mm/s; velocity and flow cm/s; O2 vol% (calibrated); CO2 vol%; CO ppm; thickness mm; width cm; rod diameter mm; burn time min. Missing values are `null`, never zero or estimated.

## Versioning

Additive changes (new fields, new endpoints) keep `/api/v1`. Removing or renaming a field or changing its meaning requires `/api/v2`. `bundle_version` changes when curated content changes.
