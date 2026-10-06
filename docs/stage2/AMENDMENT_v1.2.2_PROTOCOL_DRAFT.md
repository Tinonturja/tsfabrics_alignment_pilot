# Amendment v1.2.2: protocol (DRAFT, not adopted, not hashed)

Status: draft written 2026-10-07 for Tinon's review. Nothing in sections 3 and 4 has been evaluated. When Tinon
approves the text, its SHA-256 is recorded in the decision log **before** any candidate rule is run on any data.
If he changes anything, the changed text is what gets hashed.

## 1. Why an amendment is needed

Stage 2 run 1 (`STAGE2_RUN1_DIAGNOSIS.md`) found three specification problems, none of them a code error:

1. **Motion consistency rule (section 7 items 3 and 4).** In the fast G1 scenarios the per-frame displacement
   alternates between about -117 and -140 px, and there are occasional duplicated (0 px) and doubled or tripled
   steps. The +/-20% band around the running median of single-frame displacements sits on the edge of the
   alternation, so A-G4's tau_r is undefined (best consistency 93.6%). The same band would mislabel genuine
   alternation frames as unreliable in Stage 3.
2. **AT-04b** cannot be met by any correct float32 implementation of the frozen distance formula. The squared
   distance amplifies the expected 1e-7 feature difference by about 2 x ||q||^2 / max distance.
3. **AT-06b** uses a validation scenario whose motion estimates alias (22% point the wrong way). Its block-mean
   images cannot show warp direction.
4. **AT-03** is at risk at full scale for the same reason as AT-04b (smoke: 4.6e-5 of a 1e-4 limit with a
   320-vector coreset).

Under the frozen rules Stage 3 may not start (section 23, failure consequence), so an amendment is required to
proceed at all.

## 2. Data-access declaration

At the time this draft was written:

- No test-scenario label, anomaly map, score or metric had been computed or viewed.
- Seen and used to motivate this draft: Stage 2 run 1 phase A results; the label-free phase-correlation output
  (dx, dy, r) of all 13 pilot scenarios. These include the test scenarios of each fold, as training-side data of the
  other fold. Also seen: the smoke run's AT-02, AT-03, AT-04a and AT-04b numbers on validation frames.
- In particular, the observation that **two consecutive G1 displacements sum to an almost constant value (median
  -248 px, IQR 10 px)** was made on these data and motivates candidate M1. This must be disclosed with any result.
- A-G1's own C0c fraction (motion-unknown share of its test frames) has **not** been computed.

## 3. Proposed changes

### C1. Motion consistency: candidate M1 (two-frame displacement)

Replace "dx" by the two-frame displacement S_t = dx_t + dx_(t-1) in the consistency clause of section 7 item 3
(tau_r) and the reliability clause of item 4. Everything else in section 7 is unchanged: the |dx| <= 400 and
|dy| <= 16 checks on the single frame, the r threshold, the 0.01 grid, the 1,000-pair and 95% conditions, the
held/unknown rules, U(t, i) built from single-frame dx, and k_t from single-frame |dx|.

- **Item 3 (tau_r):** pair t is consistent iff |dx_t| <= 400, |dy_t| <= 16 and, when t - 1 also has an estimate
  and at least 5 earlier values of S exist in the scenario, |S_t - median(previous up to 15 values of S, any r)| <=
  max(16, 0.2 x |that median|). If t - 1 has no estimate, pair t is judged by the single-frame checks only.
- **Item 4 (reliable at t):** r_t >= tau_r, |dx_t| <= 400, |dy_t| <= 16; frame t - 1 has an estimate that itself
  passes r >= tau_r, |dx| <= 400 and |dy| <= 16 (otherwise frame t is not reliable); and once at least 5 earlier
  reliable values of S exist: |S_t - median(last up to 15 reliable S)| <= max(16, 0.2 x |median|). The condition on
  t - 1 uses its raw estimate, not its status, so one failed frame cannot block every later frame.
- **Why two frames.** The band is meant to catch estimation failures, not real speed changes. Speed measured over
  two frames averages out the camera's alternating frame interval. The constants 16 px and 0.2 are the frozen
  8 px and 0.2 scaled to a two-frame interval. No new threshold is introduced.
- **Known cost.** A duplicated or dropped frame changes two consecutive sums and still counts as inconsistent.
  Real motion during a dropped frame is then held at the last reliable dx, as under the frozen rule.

M1 is the **only** candidate. If M1 fails the synthetic calibration in section 4, the frozen rule stays and A-G4
remains motion-invalid. No second candidate will be tried.

### C2. AT-04b

Replace the criterion with two parts, both required:

- features of validation frames 1 to 10, batch 1 vs batch 4: rel <= 1e-6 (the size the preregistration itself
  expected, section 6 "Batch" row);
- maps, same frames, all six coresets: rel <= 1e-4 (the AT-04c map tolerance).

### C3. AT-03

Keep the 1e-4 criterion as primary. Add a pre-declared fallback, used only if the primary fails: for every query,
|d32 - d64| <= gamma x (||q||^2 + ||b*||^2), where b* is the float64 nearest neighbour and gamma = n u / (1 - n u)
with n = 1,026 and u = 2^-24 (gamma = 6.12e-5). This is the standard worst-case rounding bound for an inner product
of length n in float32, applied to the expansion terms. It is a property of float32 arithmetic, not a value fitted to
these data. Argmin agreement stays reported and not gated.

### C4. AT-06b

Replace the validation scenario by the two G2 scenarios with clean motion, T1_S164_I192_1 and T1_S164_I193_1. They
are training-side in both folds and a test scenario in neither. Images are read for the motion test only, never by
the detector. Procedure as DL-0013, per fold: scan I192 then I193 for the earliest run of 200 consecutive reliable
frames; if none, take the first 200 reliable frames in that order; both MSEs on the cells valid for U and -U; pass
at >= 190 of 200. Also report, not gated, the MSE at zero shift.

## 4. Synthetic calibration of M1 (run before any real-data evaluation)

Label-free synthetic displacement sequences, 2,000 frames each, 200 replicates per family, seeds `[20261007, family,
replicate]` with `numpy.random.default_rng`. Every family uses a "true" displacement plus estimation noise N(0, 2 px).

| Family | True displacement per frame | Estimation failures injected |
|---|---|---|
| F1 steady | constant -118 px | none |
| F2 alternating | -117, -140, -117, ... | none |
| F3 alternating + drops | F2, with 1% of frames doubled and 0.5% set to 0 | none |
| F4 steady + failures | constant -118 px | 5% replaced by uniform(-400, 400), 5% by -118 + k x 85 with k in {-2, -1, 1, 2} |
| F5 alternating + failures | F2 | as F4 |
| F6 slow steady + drops | constant -39 px, 2% doubled, 1% tripled | none |

Criteria, fixed now, for M1 and reported side by side for the frozen rule:

- **True-motion acceptance:** in F1, F2 and F6, at least 99% of frames without an injected event are consistent.
- **Failure detection:** in F4 and F5, at least 90% of frames carrying an injected failure are inconsistent.
- **No regression:** in F1 and F4, M1's results are within 1 percentage point of the frozen rule's.

M1 is adopted only if all three criteria hold. The calibration code and its output are hashed and committed.

## 5. Evaluation on real data (once)

If M1 passes section 4, tau_r is recomputed for both folds under M1 from the run 1 motion files (hashes in
`phase_A.json`). Whatever comes out is final, including "undefined". Stage 2 is then rerun in full on Kaggle with the
v1.2.2 code. Every Stage 1 test is rerun because `motion.py` changes.

## 6. Unchanged

Everything not named in section 3: folds, bank, detector, distance definition, variants, controls, windows,
events, metrics, chance gate (v1.2.1), bootstrap, decision machine, thresholds, sensitivity analyses, and the
three-stage protocol.
