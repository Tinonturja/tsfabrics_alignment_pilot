# Stage 2, run 1 (Kaggle version 1, 2026-10-06): failure diagnosis

Run: notebook version 1, Tesla T4, files fingerprint `b918ed8b...` (identical to the tested tree), report SHA-256
`51a270cc...`. Result FAIL at phase A; phases B to E of the full run did not execute. The smoke run (capped sizes,
not a record) ran every phase. No test-scenario label, map or score was computed or viewed. Every read stayed inside
the allow-lists (0 violations).

Data used for this diagnosis: `stage2_out/phase_A.json`, `stage2_smoke/phase_B.json`, `stage2_smoke/phase_D.json`,
and the 13 `stage2_out/motion/motion_<scenario>.npz` files (SHA-256 verified against `phase_A.json`). The motion
files are label-free phase-correlation output on training-side scenarios (section 24 allows inspecting them). They
include the test scenarios of the other fold.

## 1. tau_r is undefined for A-G4 (C0c: A-G4 motion-invalid)

The pipeline's tau_r was reproduced independently from the motion files: A-G1 0.00, A-G4 undefined.

| tau | A-G1 pairs | A-G1 consistent | A-G4 pairs | A-G4 consistent |
|---|---:|---:|---:|---:|
| 0.00 | 31,711 | 95.3% | 50,493 | 87.7% |
| 0.50 | 27,654 | 96.2% | 45,639 | 89.1% |
| 0.70 | 26,890 | 97.3% | 24,801 | 92.4% |
| 0.75 | 25,866 | 98.0% | 7,765 | 93.6% |
| 0.80 | 23,772 | 99.2% | 326 | 46.0% |

A-G4 never reaches 95% consistent with at least 1,000 pairs.

Per scenario (consistency as in section 7 item 3):

| Group | Scenario | dx median (px) | IQR (px) | consistent |
|---|---|---:|---:|---:|
| G1 | T1_S148_I108_1 | -119.7 | 23.7 | 81.8% |
| G1 | T1_S148_I108_2 | -119.9 | 23.8 | 83.4% |
| G1 | T1_S174_I108_1 | -118.1 | 23.5 | 76.5% |
| G1 | T1_S174_I111_1 | -118.2 | 23.2 | 89.0% |
| G1 | T1_S177_I108_1 | -118.3 | 23.2 | 88.7% |
| G2 | T1_S164_I192_1 / I193_1 | -86.2 / -86.3 | 4.1 / 4.0 | 99.9% / 99.4% |
| G2 | T1_S164_I199_1 (validation) | -86.3 | 163.8 | 28.0% |
| G3 | T1_S164_I36_1 / T1_S179_I35_1 (dark) | 0.0 | 0.2 | 99.7% / 99.8% |
| G4 | T1_S478_I118_1 / I118_2 | -39.4 / -39.0 | 2.1 / 2.0 | 89.6% / 91.6% |
| G4 | T1_S555_I117_1 | -38.9 | 1.7 | 99.6% |

**Cause.** The G1 estimates are not noisy; the per-frame displacement itself is irregular.

- In G1 it alternates between about -117 and -140 px from one frame to the next (for example -141, -117, -140,
  -118, -142, ...). The sum of two consecutive displacements is almost constant (median -248 px, IQR 10 px), and
  consecutive deviations are anti-correlated (lag-1 correlation -0.56 in T1_S174_I111_1). This looks like uneven
  frame timing in the recording, not estimation error.
- The section 7 consistency band is +/-20% of the running median (about +/-24 px). The alternation sits on the edge
  of that band. Of G1's 5,433 inconsistent pairs, 3,938 (72%) deviate by 1 to 1.5 times the band width; 838 are
  near-zero or doubled/tripled steps (duplicated or dropped frames); 657 are other.
- G4 is steady (about -39 px) except for doubled and tripled steps (686 pairs, 2.8%), which also look like
  dropped frames.

**Consequence under the frozen rules.** A-G4 is motion-invalid. With one invalid fold the decision machine gives B*
(final I), or M/G if A-G1 is also invalid. A, C, D and E are unreachable.

**Related design issue (not evaluated).** The same +/-20% band decides `reliable` frames in Stage 3. On A-G1's test
scenarios (G1) it would mark many alternation frames unreliable and `held` with the other mode's displacement
(about 3 cells wrong), which degrades V4 there. A-G1's own C0c fraction was deliberately not computed: it is a
Stage 3 validity quantity, and computing it now would inform any rule change.

## 2. AT-06b fails for A-G1 (92 of 200)

- The shifts used are steady (194 of 200 are 10 or 11 cells, matching about -86 px).
- The validation scenario's raw estimates show aliasing: 22% point the wrong way (+86, +169 px) and many are 2x or
  3x the median (-171, -256 px). Values cluster at multiples of about 85 px. The most likely reading is a fabric
  pattern that repeats about every 85 px, the same as the per-frame displacement, so shifts of -1, +1 or 2 repeats
  look alike. On 8 x 8 block means a shift of one repeat then barely changes the image, and the forward and reverse
  warps cannot be told apart. The win/loss streaks in the 200 pairs fit this.
- Not a sign error: the synthetic direction tests pass and the shift sign matches leftward motion. A direct check
  (error at zero shift versus +/-U on these frames) needs the validation images and was not run.

## 3. AT-04b fails (smoke run)

| Measure (frames 1 to 10) | Value |
|---|---|
| Features, batch 1 vs batch 4 | rel 2.4e-7 |
| Maps, batch 1 vs batch 4, six coresets | rel 2.6e-6 to 1.1e-5 (limit 1e-6) |
| AT-04a, same batches twice | bit-identical |

The convolution results differ at the 1e-7 level between batch sizes, as the preregistration expected for features.
The map is a squared distance computed as ||q||^2 + ||b||^2 - 2 q.b. Its error is about 2 x (||q||^2 / max distance)
x the feature error. In the smoke run that ratio is about 15 (max query ||q||^2 = 17.3, max distance 1.1). This
reproduces the observed 4e-6 to 1e-5. No correct float32 implementation of the frozen formula meets 1e-6 on maps.

## 4. Risk carried forward: AT-03 at full scale

Smoke AT-03 passed (error 4.6e-5 and 1.7e-5 of the largest distance; limit 1e-4; argmin agreement 100%; faiss shows
the same error size). The smoke coreset had 320 vectors. With 24,000 vectors the nearest distances shrink while
the float32 error stays near 5e-5 in absolute terms, so AT-03 may fail at full scale for the same reason as AT-04b.

## 5. What is not in question

AT-01, AT-02 (rel 1.4e-7 against the official PatchCore path), AT-04a, the coreset reproducibility, the access gate
and the unit tests all passed. No training-side frame lacked a motion estimate (U-I1 can be closed).
