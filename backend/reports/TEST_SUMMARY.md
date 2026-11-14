# Test summary — 2026-11-14

| Suite | Command | Result |
| --- | --- | --- |
| Build: ingestion + 51 scientific consistency checks | `python -m ember.build` | 51 passed, 0 failed (`build_and_consistency.txt`) |
| Python tests: ingestion, consistency (incl. 6 negative tests that break a rule on purpose), search, API, error handling, FastAPI parity | `python -m pytest` | 46 passed (`pytest_results.txt`, `pytest_junit.xml`) |
| Worker tests: 79 golden request cases replayed against the Worker service + 6 fetch-handler tests (CORS, OPTIONS, HEAD, cache headers, 405, URL decoding) | `cd worker && npm test` | 86 passed (`worker_node_tests.tap`) |
| Worker build | `npx wrangler deploy --dry-run` | Bundled, 416 KiB (62 KiB gzip), no bindings (`wrangler_dry_run.txt`) |
| Worker in Cloudflare's local runtime (workerd via `wrangler dev`), all 79 golden cases over HTTP | manual run | 79 match, 0 mismatch |

Golden cases cover every endpoint, every filter type, search and ranking queries, and all error codes (400 unknown/duplicate/missing/invalid parameter, 404, 405).
