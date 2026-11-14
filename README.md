# ARCAUS — Approved Reference-Locked Frontend

**The desktop opening screen at widths >=1280px uses the exact approved 1671×941 visual supplied by the project creator.** No AI reinterpretation is used. Its buttons, study tiles, evidence comparisons, scientific indicators, chart markers and navbar are independent keyboard-focusable HTML hit targets. Clicking a study/comparison navigates into genuinely rendered, source-backed content below. Clicking a chart median shows a grounded detail dialog; the full scientific scatterplot is interactive further down the page.

At widths below 1280px, the mobile/tablet responsive native HTML/SVG frontend is used. The first-fold reference artwork is not an image of real NASA experiment measurements; the spherical flame remains labeled illustrative artwork. The wider evidence sections use `data/evidence_bundle.json` as the offline source, or an explicitly configured public API URL in `config.js`.

## Preview without deployment

```bash
cd site
python3 -m http.server 8000
# visit http://localhost:8000
```

## Cloudflare Workers static asset hosting

This repository root contains `wrangler.toml` with asset directory `./site` and SPA fallback. Connect this repository to an existing **frontend-only** Cloudflare Worker `arcaus` only after reviewing its existing configuration and ensuring it is not also hosting your research backend. Never deploy this static frontend over the evidence API Worker.

- The frontend can show the 31 curated scientific findings, 5 cross-study comparisons, 18 BASS-II PMMA test-run mean spread rates, 27 fabric records, 16 NASA research sources and their conditions without a live backend.
- To connect the evidence backend, set ONLY the PUBLIC base URL in `site/config.js`, e.g. `window.ARCAUS_API_BASE = 'https://YOUR-BACKEND.workers.dev/api/v1'`. The API must implement the existing API contract and CORS.
- `GEMINI_API_KEY` is never stored in GitHub or frontend JavaScript. Set it as a secret on the **backend** Worker. The Ask ARCAUS feature appears only after backend connectivity.

## Exactly what is reference-image backed?

The desktop first fold is a lossless photographically faithful representation of the user-approved design with semantic interactive overlays. It is **not** a live DOM-rendered graph in that first fold. The live full-size BASS-II chart and research data sections below are real JavaScript/SVG, backed by the NASA evidence bundle. This protects exact visual fidelity while preserving scientific interactivity. To later rebuild the opening screen as editable native components, retain this approved PNG as the regression-test target.

## Roles

ChatGPT owns frontend visual design and code. Claude should work only on GitHub ↔ Cloudflare connectivity, verified research API deployment and Gemini secret, with no visual design changes. See `CLAUDE_BACKEND_ONLY.md`.

## Research Experience v2.1 (review candidate)

This version adds richer data visualizations, comparison study lanes, in-page experiment graphics and an expanded independent project summary. Read `RESEARCH_V2_CHANGELOG.md` for precise design, behavior, and science constraints.

Additional frontend files (both required for deploy):
- `site/research-upgrades.css`
- `site/research-upgrades.js`

Use the separate `ARCAUS_RESEARCH_v2_OFFLINE_PREVIEW.html` to review this candidate without Cloudflare, or serve `site/` with a local static server. The GitHub ZIP is source-only; do not upload the ZIP file itself into the repository. The creator's prior approved desktop opening frame and the NASA evidence bundle are unchanged. Deployment is gated on preview approval.
