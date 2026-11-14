# New scientifically supported findings (this round)

What changed in the evidence since the corrected Cross-Study Evidence Brief. Finding IDs refer to `FINDINGS_CATALOG.md` and `/api/v1/findings/{id}`.

## From the Saffire-V structured-PMMA presentation (ICES-2021-218)

1. **Ribs speed up opposed flame spread over thick PMMA, and narrower ribs more so; a 10 mm rib is only slightly faster than a flat plate** (F-S5-01). Author conclusion based on per-rib flame tracking that is not reproduced in the PDF, so no spread rates can be quoted.
2. **Wider ribs carry independent edge flames, and a flame that reaches the leading edge stays there** (F-S5-02). Author observation.
3. **Flames reach a finite length because the flame shields the material beneath it from oxygen, and flames in another flame's oxygen "shadow" go out** (F-S5-03). Author interpretation; NASA's Saffire IV/V overview reports the same shadowing of downstream flames.
4. **Small disturbances in the incoming flow, here from remnants of the earlier cotton burn, increased propagation speed and changed ignition to a deflagration type** (F-S5-04). Author conclusion supported qualitatively by flow visualisation; no numeric change reported.
5. **Disturbing a stratified microgravity fire during firefighting could cause a backdraft** (F-S5-05). Hypothesis only: deduced, not tested.

Test identity resolved: the ribbed sample is Saffire **V-4**, run in opposed flow at 20 cm/s. NASA's as-executed matrix gives 72.6 kPa and 25.7 mol% O2; the ZARM slides give 761 hPa and 26.9 vol% inflow. Both are reported.

## From the Saffire IV and V overview (Urban et al. 2021)

6. **At increased oxygen and reduced pressure, flames survived reduced and stopped flow and could reignite** (F-S45-01). Cotton jersey (V-2) was not quickly extinguished in still air; a PMMA flame survived a 15 s no-flow interval and reignited after 6.4 s of local extinction. Author conclusion from flight video.
7. **A small residual flow may sometimes extinguish better than no flow** (F-S45-02). Hypothesis.
8. **Thick-fuel flames reached finite size, concurrent flames stayed pinned to the leading edge, and a flame jumped a 4.5 cm gap** (F-S45-03). Author conclusion.

## Cross-study result that is new

9. **Ventilation shutdown behaves differently across atmospheres** (CMP-05). BASS-II flames always went out when the fan stopped in ISS-like air at about 1 atm; Saffire V flames at 70.7–72.6 kPa and 25.4–26.2% O2 did not reliably go out. Two separate experiments by an overlapping NASA Glenn team. Supports the 2019 authors' warning that the ISS fan-off practice may not transfer to exploration atmospheres. Not an operating guideline.

## Reconciled or corrected

10. **The 24-test rod count is right** (F-OF15-01). Olson and Ferkul 2015 reports 24 concurrent-flow rod tests; the Summary Report's 27 include O20–O22 run in February 2016, after that paper. Its blowoff line extrapolates to 13.3% O2 at zero stretch.
11. **Median per-test spread at 1 mm is 0.0895 mm/s**, not 0.090 as previously rounded (F-B2-01). Caught by the automated reproduction check.

## Unchanged and still held back

Within-BASS-II flow effect on thick-PMMA spread (confounded); any pooled predictive model; any safe-flow or safe-oxygen threshold; any lunar or Martian extrapolation.
