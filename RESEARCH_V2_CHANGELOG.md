# ARCAUS Research Experience v2.1 — review candidate

**Status: frontend preview candidate, not deployed.** The approved 1671 × 941 hero is **unchanged** as an exact image-backed view at desktop widths >=1280px. Only the research content below the opening fold was expanded. The NASA evidence bundle is byte-identical to the last approved version. Do not overwrite Claude's independent backend Worker.

## 01 — What survives comparison? (Findings)
- Kept all five source-backed scientific comparison questions.
- Added an interactive **Visual Evidence Map**, with separate study lanes, finding-type bars, source links, displayed experimental conditions, and clickable investigation focus.
- Graph bars represent **counts of curated source-backed finding records, NOT comparable measurements, statistical independence, fire risk, or experimental frequencies**.
- Clearly labels measurements, NASA author conclusions, hypotheses; repeats strict no-numeric-merge / no-threshold restrictions.

## 02 — Inside the experiment (Data)
- New focused dark-plum **Materials Lab** backdrop and grid-accent panels, visually separate from the expansive nebula stage.
- New real test-level PMMA scatterplot with switchable axes: material thickness, initial oxygen, minimum tracked airflow. Each point is an actual test mean and opens its conditions. No regression or prediction.
- Added a **within-one-PMMA-test flow-step profile**, with a test selector, actual recorded step values, and time/flow confounding caveat.
- Retained real NASA fabric outcome bars and added an **interactive 27-test tile matrix**, outcome filters, sample-reuse indicators, and test notes.

## 03 — Explore the experiments (Experiments)
- Added a seven-investigation **interactive visual atlas** with diagrams representing fuel configurations (solid-fuel duct, spacecraft fire, PMMA sphere, droplets, heated/smoke material).
- **Illustrative conceptual diagrams only**. Not NASA photography, frames, physical simulations, videos, or assertions about exact apparatus dimensions.
- Clicking any experiment selects an **in-page scientific dossier**, not an external website.
- Test-level measurements are available only for BASS-II; studies without that data are clearly labelled.

## 04 — Sources (Resources)
- Intentionally preserved the functioning source ledger and verified original-paper links.

## 05 — Research summary (About/Transparency)
- Expanded into a full research narrative: question, inputs, what was verified, original test-level statistical observations, major findings, methodological cautions, scientific contribution, four-stage research process, independent provenance, and creator attribution.
- All numerical figures are computed or recorded in the existing verified bundle. No predictive safety thresholds or untested scenario simulations.

## Source integrity
- `site/data/evidence_bundle.json` is unchanged from the prior reference-locked package.
- 7 study records; 16 source records; 31 curated findings; 5 cross-study comparisons; 18 BASS-II PMMA test runs; 39 tracked PMMA spread steps; 27 fabric records.
- Desktop homepage pixel difference versus approved `ARCAUS(3).png` at 1671 × 941: **0**, per local Chromium screenshot regression.
- Chrome/Chromium offline preview QA: navigation, chart axis changes, 18 selectable PMMA markers, PMMA flow step selection, fabric test filtering, study gallery, comparison study lanes; no JS errors or horizontal overflow at 1671 / 820 / 390 widths.
- **NOT TESTED**: Real Cloudflare production hosting, live Gemini responses, live API networking, GitHub CI, or production user flows. They remain the backend/deployment owner's scope.

## Code ownership
- Approved visuals, research UX, research CSS, diagrams and interactions: frontend owner.
- Backend deployment, GitHub/Cloudflare link, real Gemini key secret, API hostname: Claude, with zero redesign authority.
- Do not upload this review candidate to GitHub/Cloudflare until the creator approves it.
