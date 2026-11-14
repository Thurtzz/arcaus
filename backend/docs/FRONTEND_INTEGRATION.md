# Frontend integration

For the EMBER / ORBIT frontend. No frontend files are part of this package.

## 1. Point the frontend at the API

| Environment | Base URL |
| --- | --- |
| Local, Cloudflare runtime | `http://127.0.0.1:8787/api/v1` after `cd worker && npx wrangler dev` |
| Local, Python | `http://127.0.0.1:8787/api/v1` after `uvicorn ember.api:app --port 8787` (OpenAPI UI at `/docs`) |
| Production | `https://ember-orbit-evidence.<your-subdomain>.workers.dev/api/v1` after `npx wrangler deploy` |

Both local servers return identical JSON. CORS allows any origin; no auth, no keys.

If the frontend is a Cloudflare Pages site, either call the Worker URL directly or add a Pages route that proxies `/api/*` to the Worker. No other infrastructure is needed.

```js
const API = import.meta.env.VITE_EVIDENCE_API ?? "http://127.0.0.1:8787/api/v1";

async function api(path, params = {}) {
  const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== ""));
  const res = await fetch(`${API}${path}${qs.size ? "?" + qs : ""}`);
  const body = await res.json();
  if (!res.ok) throw Object.assign(new Error(body.error.message), body.error); // {code, message, details}
  return body; // {data, meta}
}
```

Do not send parameters with empty values: the API rejects unknown, duplicate or empty parameters with 400 by design.

## 2. Screen-by-screen mapping

| UI need | Call | Notes |
| --- | --- | --- |
| Investigation cards | `GET /studies`, then `/studies/{id}` | Show `independence_from_bass2` and `data_in_service` on each card |
| "Which investigations answer my question?" | `GET /rank/investigations?q=…` | Show `supporting_findings` and `matched_terms` as the reason for the rank |
| Evidence search box | `GET /search?q=…&type=finding` | Filters: `evidence_type`, `study`; show `meta.total_matches` |
| Finding detail panel | `GET /findings/{id}` | Render `evidence_type_label` as a badge, `limitations`, each `source_refs[].locator` with `source.url` |
| Cross-Study Evidence Cards | `GET /comparisons`, then `/comparisons/{id}` | One row per `rows[]`; show `independent_experiment_count` and `independence_note`; never draw a shared numeric axis (`numeric_merge_allowed` is false) |
| Data gaps panel | `GET /gaps?status=open` | |
| BASS-II spread vs thickness chart | `GET /bass2/pmma/tests` | One mark per test (`spread_mean_mm_s`), bar from `spread_min_mm_s` to `spread_max_mm_s`; encode `width_cm` and `sides_burning` |
| BASS-II within-test sequence chart | `GET /bass2/pmma/steps?tracked=true` | Draw each `test_id` as a path in `step_order`; show `meta.warning` |
| Fabric flammability map | `GET /bass2/fabric/outcomes` | x = `flow_final_cm_s` (log), y = `o2_vol_pct`; marker by `outcome_class`; fade `sample_reused`; line from `flow_start_cm_s` when `flow_was_changed`; label quench points as upper bounds |
| Test drill-down | `GET /bass2/tests/{test_id}` | Includes steps, fabric outcome, findings, `appendix_observation_machine_extracted` (label it "machine-extracted log text") |
| Headline statistics | `GET /bass2/summary` | Use these values; do not recompute in the browser |
| Footer / about | `GET /meta`, `GET /health` | Show `content_sha256` (first 12 characters) and `checks_passed` |

## 3. Display rules (scientific accuracy)

1. Every finding shown carries its evidence badge: Verified measurement, Author conclusion, or Hypothesis.
2. Never present a hypothesis as a result, and never present an author conclusion as verified data.
3. Do not plot BASS-II, Saffire and SoFIE-GEL values on one numeric axis.
4. Do not fit lines, boundaries or predictions to any BASS-II chart.
5. Show sample sizes (`meta.count`) in chart subtitles.
6. Show `meta.warning` text on BASS-II charts where present.
7. Do not show lunar or Martian predictions; there is no data for them here.
8. If the backend returns `"status": "degraded"` from `/health`, show a banner: data failed a consistency check.

## 4. If an AI explanation layer is added later

Gemini or any model is deferred. When added, it should only receive records returned by `/search` or `/findings/{id}`, quote `source_refs` for every sentence, and answer "not in the evidence" when search returns nothing. The retrieval API is already the grounding layer.

## 5. Updating evidence

Edit `data/curated/*.json`, run `python -m ember.build` (must print `0 failed`), run the tests, then `cd worker && npx wrangler deploy`. The frontend needs no change for new findings or comparisons.
