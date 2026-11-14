# Saffire-V structured-PMMA review (ICES-2021-218)

Source: Eigenbrod, Meyer, Jomaas, Urban, Ruff, Olson, Ferkul, Toth, *Opposed Flame Spreading along a Structured PMMA-Sample in Exploration Atmosphere under Microgravity*, 50th ICES, 2021. NTRS 20210017838. The file is a 12-slide presentation (SHA-256 7d604353…fb5b), read slide by slide as images. Cross-checked against Urban et al. 2021 (NTRS 20210017780), NASA's Saffire IV and V overview.

## Experimental conditions documented

| Item | Value | Where |
| --- | --- | --- |
| Vehicle | Cygnus, flight NG-14, January 2021 | Slides 3–5 |
| Flow duct | 1,320 mm long, 450 mm wide, 300 mm high | Slide 3 |
| Inflow schedule | 20 cm/s for 360 s, then 5 cm/s for 300 s, then off | Slide 3; text |
| Atmosphere (ZARM) | 761 hPa, 26.9 vol% O2 (labelled "Inflow") | Slide 3 |
| Atmosphere (NASA, as executed) | Test V-4: 72.6 kPa, 25.7 mol% O2, 20 cm/s, opposed, 20 cm length | Urban et al. 2021, slide 5 |
| Sample | Cast PMMA, 200 × 400 mm, 10 mm base, ribs 3 mm high on both sides (16 mm total), rib widths 1–10 mm in 1 mm steps, 2 cm between rib faces | Slide 5 drawing; Urban slide 12 |
| Card layout | Test 2 cotton fabric upstream of the structured PMMA (Tests 1 and 4) and 1-sided PMMA (Test 3); "planned test logic" | Slide 4 |
| Ignition | Kanthal wire; ignition time 61.842 s shown in tracking frames | Abstract; slides 7–9 overlay |
| Flow visualisation frame | Inlet flow 19.8 cm/s shown | Slides 6, 10 overlay |

The two atmospheres disagree. The NASA overview is labelled "as executed" and the ZARM value is labelled "Inflow", so the service reports the as-executed values first and both (gap GAP-01).

## Measurements available

| Slide | Content | Numeric data recoverable? |
| --- | --- | --- |
| 6, 10 | Flow visualisation images, inlet-flow trace | Images only; one inlet value (19.8 cm/s) in the overlay |
| 7 | Flame-front tracking per rib (position from upper end, mm, vs time, s; inlet flow, cm/s) | **No.** Axes and legend only (ribs 1–10 and flat); data series are absent in the PDF |
| 8 | Flame length tracking (mm vs s) | **No.** Axes only |
| 9 | Flame flickering (mean flame intensity vs s) | **No.** Axes only |

No graph values were digitized, estimated or simulated.

## Conclusions, classified

| Author statement (slide 11) | Classification | Basis | Service finding |
| --- | --- | --- | --- |
| Ribs significantly accelerate opposed spread; the narrower the rib, the more | Author conclusion, measurement-based (tracking not shown) | Flame-front tracking per rib | F-S5-01 |
| Spread along the 10 mm rib only slightly faster than a flat plate | Author conclusion, measurement-based (not shown) | Same | F-S5-01 |
| Wider ribs show more independently propagating edge flames | Author observation | Video | F-S5-02 |
| A flame reaching the leading edge dwells there and spreads only across the edge | Author observation | Video | F-S5-02 |
| Flame lengths are finite because material under the flame is shielded from oxygen ("shadowing") | Author interpretation (mechanism) | Finite flame length observed; no local O2 measured | F-S5-03 |
| Flames in the shadow of other flames extinguish | Author interpretation | Observation plus mechanism | F-S5-03 |
| Concurrent flame propagation is unlikely | Hypothesis (generalization from an opposed-flow test) | Not explained in slides | F-S5-06 |
| Small stratification perturbations considerably increase propagation velocity | Author conclusion | Flow visualisation shows disturbed flow from cotton remnants and deviating progress at ribs 8–10 | F-S5-04 |
| Disturbing stratification during firefighting could cause dangerous backdraft | Hypothesis | Deduced; not tested | F-S5-05 |
| Microgravity combustion produces much larger quantities of combustible flue gas than ground fires | Hypothesis-level claim in this source | Not measured in the slides; consistent with BASS-II fuel-rich burning (F-B2-10) | F-S5-05 |
| Small inflow disturbance delayed ignition and caused deflagration-type ignition | Author observation (single event) | Video | F-S5-04 |

## Related NASA statements (Urban et al. 2021)

- Flames reached nearly steady lengths in all configurations; thick-fuel concurrent flames stayed pinned to the leading edge; downstream flames were inhibited by the upstream flame's oxygen shadow; a flame jumped a 4.5 cm gap (slide 13) → F-S45-03.
- At increased oxygen, extinguishment in still air cannot be assumed to be rapid; a PMMA flame survived a 15 s no-flow interval and reignited after 6.4 s of local extinction (slides 7–8) → F-S45-01.
- A small residual flow may help extinction more than none (slide 9) → F-S45-02 (hypothesis).

## Visualization data availability (task 5)

| Candidate | Status | Provenance |
| --- | --- | --- |
| Numeric flame-front or flame-length tracking for Saffire-V | **Not available.** Blank in the presentation PDF; the written ICES-2021-218 paper was not obtained | ZARM, University of Bremen |
| Saffire-V raw video or image sequences | **Not found publicly.** No PSI record for Saffire IV–VI in mirrored PSI catalogs (2026-11-13); NASA Glenn's Saffire data portal is "authorized users only" | NASA GRC |
| Saffire-V public video | A NASA image-library video titled "Saffire-V Experiment January 2021" (Jan 12, 2021, NASA GRC) is listed publicly | NASA image and video library; illustrative only, not calibrated |
| Saffire I and III image sequences | **Listed on PSI.** A third-party mirror of the PSI file inventory shows PSI-98 and PSI-100 holding raw JPEG sequences per camera, distortion grids and ROI offset documents; not downloaded or verified here | NASA PSI, CC0-1.0 |

**Recommendation.** An interactive flame-tracking feature for Saffire-V cannot be built from NASA data today. The defensible options are: (1) embed the public NASA video as an illustration, clearly labelled as video and not data; (2) build tracking on Saffire I or III, where PSI provides raw image sequences and distortion grids, after reconciling PSI with NTRS (GAP-08); (3) request the Saffire-V tracking data from ZARM. Do not draw simulated tracks and present them as NASA measurements.
