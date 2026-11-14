# CLAUDE TASK — BACKEND AND DEPLOYMENT ONLY

**IMPORTANT: Frontend visual implementation is complete and frozen.** This is the user's approved frontend work, implemented separately. Do **not** redesign, regenerate, restyle, replace, refactor, or reinterpret files under `site/` or the visual assets. No UI work is assigned to you. If a genuine technical frontend fix is unavoidable, explain the exact change first and request approval; otherwise restrict changes to infrastructure, backend code, docs and secret/config wiring.

## Your assignment

1. **GitHub repository & Cloudflare**
   - Help publish this existing directory as the source of truth in a GitHub repository with a reviewed production branch. Preserve file paths and all supplied frontend bytes.
   - Inspect the existing `arcaus` Worker in Cloudflare before changing its configuration: determine whether it serves static frontend or a mixed/backend API. **Do not overwrite an existing API Worker.** If necessary maintain two distinct Workers: `arcaus` for static site, separately named research API Worker.
   - Connect GitHub → Cloudflare Workers Builds using the supplied static-worker `wrangler.toml` (or an equivalent configuration compatible with the account). For the static project, source root is repository `/`, Wrangler asset directory is `./site` and static entry is `site/index.html`. Never deploy a README/handoff ZIP in place of the site folder.
   - Keep production auto-deploy disabled until user approves preview; explain any Cloudflare UI limitations and how to make production deploys controlled. Verify homepage `/` returns HTTP 200 and actual assets load; `/` must not 404.

2. **Evidence backend**
   - Preserve Claude's existing validated backend, its API contracts, record IDs, source metadata and classifications. `site/data/evidence_bundle.json` is the verified static fallback; DO NOT modify its research numbers to make charts look smoother.
   - Public frontend expects `site/config.js` to set `window.ARCAUS_API_BASE = 'https://BACKEND-WORKER.workers.dev/api/v1';`, where applicable. This is a **public URL only**, not a secret. If no backend is ready, leave it empty so static evidence still works.
   - Expected backend paths: `/meta`, `/health`, `/studies`, `/findings`, `/comparisons`, `/gaps`, `/sources`, `/bass2/summary`, `/bass2/pmma/tests`, `/bass2/fabric/outcomes`, `/search`, and `/ask` when Gemini is available. Handle CORS for the production frontend origin and errors gracefully.
   - Do not expose Gemini API key in `site/config.js`, GitHub, screenshots, logs or any browser-delivered JS. Set `GEMINI_API_KEY` as an encrypted secret on the **backend** Cloudflare Worker only. Verify one real grounded `/api/v1/ask?q=...` answer with valid retrieved citations, and verify no-evidence and upstream-failure behavior. Do not claim Gemini live based only on mock tests.

3. **Evidence integrity and deploy QA**
   - Preserve the verified 18 BASS-II PMMA test records, 39 nested tracked steps, 27 fabric outcomes, five cross-study comparisons, and scientific source references. Do not merge incompatible experimental numerical findings. Hero orb is illustrative artwork, NOT a NASA photograph or simulation.
   - Test production URL homepage and deep links; asset/network errors; cross-origin API calls; static fallback; search; graphics; source link navigability; Gemini tool response; and mobile. Provide URLs, response codes, short logs, and a concise pass/fail report.
   - First give the user GitHub repo URL, preview/staging URL, exact deployment steps and API Worker URL. **No production deployment, backend replacement or frontend modifications without user approval.**

## Hard scope boundary

- ✅ Allowed: GitHub connection, Workers configuration, deployment/debugging, backend hosting/secret handling, API/CORS debugging, minimal public API base URL in `site/config.js` (after confirming correct backend URL), test scripts, documentation.
- ⛔ Not allowed: new frontend components, aesthetic changes, imagery substitutions, typography changes, homepage redesign, invented chart values, modifying the verified dataset, or replacing this project with an old Claude starter.

The site's visual design has already been handled by ChatGPT with the user. **Your job is to connect the infrastructure, not build the website.**

## IMPORTANT: Research Experience v2.1 review candidate

A new researcher-experience frontend candidate adds `site/research-upgrades.js`, `site/research-upgrades.css`, and updated `site/index.html`, `site/app.js`. The original approved hero art, source data, and backend API contract are unchanged. **Do not silently mix these new frontend files with your previous version.** Wait until Tiffany approves the v2.1 preview. If approved, deploy the entire supplied `site/` directory from this package as a cohesive replacement for the prior frontend; do not reproduce or revise the UI. GitHub/Cloudflare/backend/Gemini integration remain your only responsibilities.
