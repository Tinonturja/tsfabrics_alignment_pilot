# Amendment v1.2.2: protocol

Status: adopted 2026-10-07 (DL-0016). Nothing in sections 3 and 4 had been evaluated on any data when this text was
adopted. Its SHA-256 is recorded in the decision log before any calibration or real-data computation.

**Nature of this amendment.** v1.2.2 is a post-Stage-2 diagnostic amendment. It was written after Stage 2 run 1
failed, and its motion rule M1 was designed after viewing label-free phase-correlation traces from that run. M1 is
not part of the preregistration of 2026-09-27 or of amendment v1.2.1, and must never be described as preregistered.
What is pre-declared is this protocol: one candidate, fixed calibration criteria, and acceptance of whatever the
single real-data evaluation produces. The text was revised after an analytic audit (no runs) on 2026-10-07
(`AMENDMENT_v1.2.2_AUDIT.md`, changes D1 to D9).

**Decision record.** On 2026-10-07, after the audit and before any evaluation, Tinon chose band (b) for M1 (section
3, C1) and accepted changes D1 to D9.

## 1. Why an amendment is needed

Stage 2 run 1 (`STAGE2_RUN1_DIAGNOSIS.md`) found four specification problems, none of them a code error:

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

At the time this text was written:

- No test-scenario label, anomaly map, score or metric had been computed or viewed.
- Seen: Stage 2 run 1 phase A results; the label-free phase-correlation output (dx, dy, r) of all 13 pilot
  scenarios. These include the test scenarios of each fold, as training-side data of the other fold. Also seen: the
  smoke run's AT-02, AT-03, AT-04a and AT-04b numbers on validation frames.
- Viewed and used to design M1 (real data, label-free):
  - the median and IQR of the two-frame sum S_t = dx_t + dx_(t-1) on T1_S174_I111_1 (-247.7, 10.5),
    T1_S148_I108_2 (-248.6, 14.7), T1_S478_I118_1 (-79.1, 5.0) and T1_S164_I199_1 (-169.1, 184.0);
  - lag-1 correlations of single-frame deviations;
  - the frozen rule's per-scenario consistency;
  - a classification of its inconsistent pairs by size of deviation.

  The first three scenarios are test scenarios of A-G1 or A-G4, seen only as training-side motion. M1's consistency
  flags and tau_r were not computed on real data.
- Viewed: the 200 AT-06b pairs (shifts and MSEs) on T1_S164_I199_1, validation data.
- No test-scenario label, anomaly map, detector score or metric was computed or viewed. The only detector outputs
  seen are validation-frame numbers from the smoke run (AT-02, AT-03, AT-04a, AT-04b).
- A-G1's own C0c fraction (motion-unknown share of its test frames) has **not** been computed.

## 3. Proposed changes

### C1. Motion consistency: candidate M1 (two-frame displacement)

M1 replaces the single-frame displacement by the two-frame displacement S_t in the consistency clause of section 7
item 3 (tau_r) and the reliability clause of item 4. The bound checks, the r threshold, the 0.01 grid, the
1,000-pair and 95% conditions, and the held/unknown rules are unchanged.

Definitions. For a frame t with an estimate (has_est) whose predecessor t - 1 also has one,
S_t = dx_t + dx_(t-1), using raw single-frame estimates. S_t is undefined otherwise.

- **Item 3 (tau_r consistency).** The history H3 of a scenario is the list of every defined S_j, j < t, in time
  order, regardless of r, bounds or consistency. Pair t is consistent iff |dx_t| <= 400 and |dy_t| <= 16 and, if
  S_t is defined and H3 has at least 5 entries, |S_t - median(last up to 15 entries of H3)| <= B(median). If S_t is
  undefined, or H3 has fewer than 5 entries, only the two bound checks apply.
- **Item 4 (reliable at t).** Frame t is reliable iff r_t >= tau_r, |dx_t| <= 400, |dy_t| <= 16, frame t - 1 has
  an estimate with r_(t-1) >= tau_r, |dx_(t-1)| <= 400 and |dy_(t-1)| <= 16, and, if the reliable history H4 (S_j
  of every earlier reliable frame j, in time order) has at least 5 entries,
  |S_t - median(last up to 15 entries of H4)| <= B(median). Held and unknown statuses, and their 5-frame rule, are
  unchanged.
- **Band B (choice (b)).** B(M) = max(8, 0.2 x |M| / 2). This is the frozen band, in single-frame units, applied to
  the two-frame sum. It keeps the frozen sensitivity to an isolated single-frame error. The constants 8 px and 0.2
  are the frozen ones; no new threshold is introduced.
- Medians use numpy's median (mean of the two middle values for an even count). Comparisons are inclusive (<=), as
  in the frozen rule.
- Unchanged: U(t, i) from single-frame dx; k_t and m_t from single-frame |dx| of reliable frames; held
  dx = last reliable dx.
- Changed indirectly, through the statuses: the reliable set used by k_t, oracle dx, motion-unknown frames, the
  V4-family fallback, and C0c.
- Rationale: the most likely explanation of the G1 traces is an alternating frame interval. The single-frame
  displacement then alternates while the two-frame sum stays nearly constant. Testing S_t lets genuine alternation
  pass while still flagging isolated errors.
- Known costs: a duplicated or dropped frame at t makes S_t and S_(t+1) inconsistent. The frame after a frame whose
  raw estimate fails the basic checks is not reliable.

M1 is the **only** candidate. If M1 fails the synthetic calibration in section 4, the frozen rule stays and A-G4
remains motion-invalid. No second candidate will be tried.

### C2. AT-04b

Validation frames 1 to 10, computed once with batch size 1 and once with batch size 4 (batches {1-4}, {5-8},
{9-10}). Both parts are required:

- features (10 x 8,000 x 1,024): max|f1 - f4| / max|f4| <= 1e-6;
- maps under each of the six coresets: max|a1 - a4| / max|a4| <= 1e-4.

The map tolerance reuses the value of AT-04c's map criterion. AT-04c itself (start of Stage 3) is unchanged.

### C3. AT-03

Keep the 1e-4 criterion as primary.

Fallback, applied only if the primary criterion fails. For each of the 2,000 queries q:

- b* is the smallest-index float64 minimiser;
- b^ is the coreset vector the float32 computation returned;
- E(b) = gamma_1026 (||q||^2 + ||b||^2 + 2 |q|.|b|) + 1,024 x 2^-53 x d64(q, b*), all evaluated in float64.

The query passes iff |d32(q) - d64(q)| <= max(E(b*), E(b^)). The fallback passes iff every query passes.
gamma_n = n u / (1 - n u), u = 2^-24, n = 1,026: 1,024 products per inner product plus the two additions combining
||q||^2, ||b||^2 and -2 q.b.

AT-03 = PASS if the primary or, failing that, the fallback passes. Both results are recorded. Argmin agreement stays
reported and not gated. This changes only AT-03's acceptance; the detector's distance computation is unchanged.

### C4. AT-06b

Statuses of T1_S164_I192_1 and T1_S164_I193_1 are computed under the fold's tau_r with the motion rule in force (M1
if adopted, else the frozen rule). Pairs are (t - 1, t) with frame t reliable, 1-based; frame t - 1 may have any
status. U(t, 1) = floor(-dx_t / 8 + 0.5).

Selection is made from statuses alone, written to the record with its hash, and fixed **before** any image is read:

1. the earliest run of 200 consecutive reliable frames in I192;
2. else the earliest such run in I193 (runs never cross scenarios);
3. else the first 200 reliable frames of I192 in time order, continued with those of I193 only after I192's are
   exhausted;
4. if I192 and I193 together have fewer than 200 reliable frames, AT-06b = FAIL for that fold.

Images are read under purpose `motion` (both scenarios are training-side in both folds) and are never passed to the
detector. A pair holds iff the U-warp MSE is strictly smaller than the -U-warp MSE on the columns valid for both. If
no column is valid for both, the pair does not hold. Pass iff at least 190 of 200 pairs hold. The MSE at zero shift
is reported, not gated. If tau_r is undefined for a fold, AT-06b is not applicable to it.

## 4. Synthetic calibration of M1 (run before any real-data evaluation)

**Generation.**

- Families F1 to F6 have indices 1 to 6. Replicate r = 0..199 uses
  `rng = numpy.random.default_rng([20261007, family_index, r])`.
- Each trace has 2,000 frames. Frame 1 has no estimate; frames 2 to 2,000 have one, with r_t = 1 and dy_t = 0.
- Draws, in this order, each as one vectorised call of length 2,000:
  - noise = `rng.normal(0, 2, 2000)`;
  - u = `rng.random(2000)`;
  - w = `rng.uniform(-400, 400, 2000)`;
  - k = `rng.choice([-2, -1, 1, 2], 2000)`.
- Base displacement b_t:
  - F1, F4: -118;
  - F2, F3, F5: -117 at even t, -140 at odd t;
  - F6: -39.
- True displacement:
  - F3 and F6 events: doubled when u_t < 0.01 (F6: 0.02), giving 2 b_t; tripled in F6 when 0.02 <= u_t < 0.03,
    giving 3 b_t; duplicated in F3 when 0.01 <= u_t < 0.015, giving 0;
  - otherwise b_t.
- Estimate dx_t = true displacement + noise_t, except in F4 and F5:
  - failure "uniform" when u_t < 0.05: dx_t = w_t;
  - failure "alias" when 0.05 <= u_t < 0.10: dx_t = b_t + 85 k_t;
  - failures replace the estimate, with no noise added.

| Family | Base | Events |
|---|---|---|
| F1 steady | -118 | none |
| F2 alternating | -117 / -140 | none |
| F3 alternating + drops | -117 / -140 | 1% doubled, 0.5% duplicated |
| F4 steady + failures | -118 | 5% uniform, 5% alias |
| F5 alternating + failures | -117 / -140 | 5% uniform, 5% alias |
| F6 slow + drops | -39 | 2% doubled, 1% tripled |

**Sets.**

- Event frames are the frames given an injected drop, duplicate or failure.
- Affected frames are each event frame t and t + 1.
- Clean frames are frames 21 to 2,000 that are not affected. Frames 2 to 20 are warm-up and excluded for both rules.

**Rules compared.**

- The frozen rule is computed by the unchanged Stage 1 function `motion.tau_r` (consistency part) and
  `motion.statuses` (with tau_r = 0).
- M1 is computed by the new functions.
- Both are computed on the identical arrays.
- "Consistent" is the item 3 flag; "reliable" is the item 4 status with tau_r = 0.
- Proportions are pooled over the 200 replicates of a family.

**Criteria (all required, item 3 and item 4 each):**

1. F1, F2, F6: at least 99% of clean frames consistent (reliable).
2. F4, F5: at least 90% of event frames inconsistent (not reliable).
3. F1 and F4: M1's clean-frame acceptance is no more than 1 percentage point below the frozen rule's. M1's
   event-frame detection in F4 is no more than 1 percentage point below the frozen rule's.

F3 is reported, not gated. M1 is adopted only if all criteria hold. The calibration code and its output are hashed
and committed.

## 5. After the calibration

If M1 passes section 4:

1. A new configuration file `configs/pilot_v1_2_2.yaml` records M1's band and the AT changes. Its hash, and this
   protocol's hash, are logged.
2. `motion.py` gains the M1 functions. The frozen functions stay, for the comparison and the record.
3. The full Stage 1 suite is rerun on Kaggle as a new Stage 1 record for v1.2.2.
4. Stage 2 is rerun from the beginning on Kaggle. Its phase A computes tau_r per fold from its own motion estimates.
   That value is the only tau_r of record, and it is final, including "undefined". No offline computation of tau_r
   under M1 is made from the run 1 files. The rerun's motion files are compared with run 1's by hash and the
   comparison is reported.

No detector output is used in any step. If M1 fails section 4, the frozen rule stays: A-G4 is motion-invalid and
steps 1 to 4 proceed with the frozen rule and the C2 to C4 changes.

**No further amendments of section 7, AT-03, AT-04b or AT-06b are permitted in this pilot.** If any of them fails
after v1.2.2, Stage 3 does not start. The pilot is then reported as stopped at Stage 2, with the failure recorded.

## 6. Unchanged

Everything not named in section 3: folds, bank, detector, distance definition, variants, controls, windows, events,
metrics, chance gate (v1.2.1), bootstrap, decision machine, thresholds, sensitivity analyses, and the three-stage
protocol.
