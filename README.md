# ARCAUS — Fire Beyond Gravity

**An independent TERNARY project created by Tiffany Hurtado for NASA Space Apps 2026. Not an official NASA service.**

This is the actual user-interface source, built to match the **approved November 14, 2026 ARCAUS screenshot**, not a prompt or a redesign proposal. It includes a functional, accessible frontend and the existing validated NASA evidence dataset.

## What's included

- Approved-style visual structure: cinematic nav, hero introduction, conceptual flame, featured studies, three measurement panels, planetary horizon, and scientific research sections.
- Sitewide pages (same-page sections): Findings, measured Data, Experiments/Search, Resources, Transparency, optional OpenSpace external link.
- Real source-backed metrics: BASS-II 18 PMMA spread tests, 39 tracked steps, 27 fabric outcomes; descriptive median rate chart for PMMA thickness; 31 findings, 5 independent cross-study comparisons, 16 source records.
- Live API-compatible frontend; defaults to a **verified static bundle** if no backend API is set or available.
- Optional Gemini `Ask ARCAUS` panel appears only when a live API connects; it never stores a key or fakes a Gemini answer.
- Source data file: `site/data/evidence_bundle.json`, SHA-256 identifier (manifest) `7829520c83d7...`.

## Preview without a server

Open **`ARCAUS_OFFLINE_PREVIEW.html`** in Chrome, Safari, or another modern browser. That preview packages CSS, art, JavaScript, and evidence JSON into one file. All research exploration works without a server; Gemini is intentionally not active in offline mode. This is a review convenience, **not** the file to deploy.

## Local development

Open a terminal in `site/` and start a local server:

```bash
python3 -m http.server 8000
```

Open `http://localhost:8000/` in your browser. `index.html` is at the **site root**. The browser must not load JSON through `file://` for the deployable folder; use the single-file offline preview if no server is available.

## Cloudflare drag-and-drop upload

Use the contents of the **`site/` folder** (or `ARCAUS_CLOUDFLARE_UPLOAD_READY.zip`, where `index.html` sits at the ZIP root). Don't upload this whole repository folder or a screenshot/document ZIP. Confirm Cloudflare is displaying this new homepage via a cache-busting query parameter, e.g. `/?v=arcaus-direct`.

> **Important**: Static website deployment and backend API deployment are separate. Uploading the frontend will **not** deploy the Gemini Worker or set `GEMINI_API_KEY`. If `arcaus` currently hosts a different Worker, do not overwrite it until you've confirmed its role and backed up its code/config.

## GitHub → Cloudflare Workers

This repo includes a `wrangler.toml` for a **static-asset-only** Worker named `arcaus`, serving files from `./site`:

```toml
name = "arcaus"
compatibility_date = "2026-11-14"

[assets]
directory = "./site"
not_found_handling = "single-page-application"
```

Push to GitHub. For Git integration, set the project root to `/` and use `npx wrangler deploy` as the deploy command, based on the Cloudflare configuration for your account. **Do not enable automatic production deploy until a preview build is tested.** GitHub files should include source, assets and evidence bundle, never secrets.

## Connect the NASA evidence API and Gemini

The browser contains **no Gemini API key**. Edit `site/config.js` with your deployed public evidence API base:

```js
window.ARCAUS_API_BASE = 'https://YOUR-RESEARCH-WORKER.workers.dev/api/v1';
```

Or temporarily use `?api=https://YOUR-RESEARCH-WORKER.workers.dev/api/v1` for debugging. The Worker must implement `/meta`, `/studies`, `/findings`, `/comparisons`, `/gaps`, `/bass2/summary`, `/bass2/pmma/tests`, `/bass2/fabric/outcomes`, `/sources`, `/health`, `/search`, and optionally `/ask`. Since static site and API may be on different subdomains, the API must allow CORS from the public ARCAUS origin. Configure `GEMINI_API_KEY` **only as an encrypted secret on the API Worker**.

Test `/api/v1/health` and one real `/api/v1/ask?q=...` request separately before claiming Gemini works. With a 503 or 502, the site will display an explanatory error while retaining verified static research access. Never commit secrets or publicize a key in screenshots.

## Science and citation requirements

- The glowing orb is **illustrative artwork**, not experiment imagery, a numeric flame simulation, or a calibrated measurement.
- BASS-II spread steps are nested inside tests; 39 steps are **not** 39 independent experiments.
- The thickness chart displays `0.0895, 0.0509, 0.0338, 0.0359, 0.0296 mm/s` (1–5 mm medians of test means) from NASA/TM-20210011385 Table 5.1; descriptive only.
- Do not conflate BASS-II, Saffire IV/V, and SoFIE-GEL experimental conditions or treat overlapping author teams as numerical replication.
- Source evidence is classified as verified measurement, NASA author conclusion or hypothesis; scientific limitations are exposed.
- No arbitrary safe oxygen/airflow thresholds or Moon/Mars predictions are supplied.

## QA results

A desktop, tablet, and mobile Chromium renderer exercised the source code with the verified static evidence bundle (browser asset delivery was replaced with inline-only content for preview due to the restricted test environment). At 1671 px, 820 px, and 390 px:

- No uncaught page JavaScript exceptions.
- No horizontal overflow.
- 3 featured study links, 5 comparison options, 18 clickable PMMA test points, 16 NASA source records.
- Verified successful study selection, `quench` search, comparison selection, and test-point detail view.

**Not tested live:** Cloudflare deployment, real remote backend CORS, Gemini upstream call, production DNS and cache behavior. Test these in the deployed environment before final submission.
