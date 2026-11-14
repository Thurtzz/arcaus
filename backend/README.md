# EMBER / ORBIT — scientific evidence backend

TERNARY · NASA Space Apps 2026 · Flame in Freefall

A small, checked backend that serves verified NASA BASS-II data and curated microgravity fire-safety findings, with every finding classified (verified measurement, author conclusion, hypothesis), traced to a page, table, figure or slide, and labelled with its experiment lineage so publications from one experiment are never counted as replication.

- **Production server:** a Cloudflare Worker (`worker/`) that serves a prebuilt JSON evidence bundle. No database, no bindings, no AI calls.
- **Data and science:** Python (`ember/`) ingests and validates the NASA files, runs 51 automated scientific consistency checks, builds the bundle and search index, and provides a FastAPI app with identical responses for local development and OpenAPI docs.

## Quick start

```bash
pip install -r requirements.txt
python -m ember.build          # validate data, run consistency checks, write data/build/ (must end "0 failed")
python -m pytest               # 46 Python tests (also writes tests/golden/parity_cases.json)
cd worker && npm install && npm test   # 86 Worker tests: replay of all golden cases + fetch-handler tests
npx wrangler dev               # http://127.0.0.1:8787/api/v1/health
npx wrangler deploy            # production
```

Python alternative: `uvicorn ember.api:app --port 8787` (OpenAPI UI at `/docs`).

## Layout

```
data/raw/        Verified inputs: PSI-25 table (SHA-256 checked) and the validated Table 5.1, Table 7.1 and Appendix A CSVs
data/curated/    Hand-curated evidence: sources, studies (lineage), findings, comparisons, data gaps
data/build/      Generated: evidence_bundle.json (served), per-collection JSON, consistency_report.json
ember/           ingest.py · consistency.py · search.py · build.py · service.py · api.py · docs.py
worker/          Cloudflare Worker: src/index.js, src/service.js, src/search.js, tests, wrangler.toml
tests/           pytest suites: ingestion, consistency, search, API, parity
docs/            API contract, methodology, Saffire-V review, new findings, data gaps, sources, findings catalog, frontend integration
reports/         Test and build output from the last run
```

## What the service holds

| Collection | Records |
| --- | --- |
| Studies (investigations) | 7: BASS-II, BASS, Saffire I–III, Saffire IV–V, SoFIE-GEL, FLEX, SAME-R |
| Sources | 16, each with what was actually read |
| Findings | 31 (5 verified measurements, 22 author conclusions, 4 hypotheses) |
| Cross-study comparisons | 5: airflow, oxygen, geometry, quenching vs blowoff, ventilation change |
| Data gaps | 10 |
| BASS-II data | 129 tests, 41 PMMA flow steps (18 independent tests), 27 fabric outcomes |

## Documentation

- `docs/API_CONTRACT.md` — endpoints, parameters, envelopes, errors
- `docs/FRONTEND_INTEGRATION.md` — how the frontend should call and display it
- `docs/METHODOLOGY.md` — ingestion, evidence model, statistics, checks, retrieval
- `docs/SAFFIRE_V_REVIEW.md` — slide-by-slide Saffire-V review and data availability
- `docs/NEW_FINDINGS.md` — what is new this round
- `docs/DATA_GAPS.md`, `docs/SOURCES.md`, `docs/FINDINGS_CATALOG.md` — generated from the curated data (`python -m ember.docs`)

## Rules this backend enforces

Verified measurements only from verified BASS-II data. No numeric merging across experiments. No replication counted within one lineage. No imputed values. No unsourced numbers (the 0.88 mm/s Saffire-V figure is blocked by a check). The build fails if any rule breaks.
