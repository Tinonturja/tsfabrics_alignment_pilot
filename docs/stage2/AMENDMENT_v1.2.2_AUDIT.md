# Adversarial audit of the Amendment v1.2.2 draft

Date: 2026-10-07. Object: `docs/stage2/AMENDMENT_v1.2.2_PROTOCOL_DRAFT.md` (unchanged by this audit).
Nothing was run for this audit: no real-data M1, no tau_r, no synthetic calibration, no Stage 2. The figures in
B2 are arithmetic on the rule definitions, not results.

## A. Blockers

### B1. The data-access declaration is incomplete, and the status of v1.2.2 is not stated plainly

- The draft says "Nothing in sections 3 and 4 has been evaluated". That is true for M1's consistency flags and
  tau_r. But during the diagnosis I computed the **median and IQR of the two-frame sum S_t** (the quantity M1 tests)
  on four real scenarios:
  - T1_S174_I111_1: median -247.7, IQR 10.5 (G1, A-G1 test);
  - T1_S148_I108_2: median -248.6, IQR 14.7 (G1, A-G1 test);
  - T1_S478_I118_1: median -79.1, IQR 5.0 (G4, A-G4 test);
  - T1_S164_I199_1: median -169.1, IQR 184.0 (validation).

  I also computed lag-1 correlations, and classified the frozen rule's inconsistent pairs by size of deviation.
  This is partial real-data knowledge of M1's behaviour, and it must be declared.
- The per-pair AT-06b MSEs on T1_S164_I199_1 were viewed. That is validation data, allowed, but it must be declared.
- The draft never says outright that v1.2.2 is a **post-Stage-2 diagnostic amendment, not part of the
  preregistration**. Without that sentence a reader could take M1 as preregistered.
- Confirmed: no test-scenario label, anomaly map, detector score or metric was computed, viewed or used. The only
  detector outputs seen are validation-frame numbers from the smoke run (AT-02, AT-03, AT-04a, AT-04b).

### B2. M1's tolerance hides a degree of freedom and doubles the tolerated single-frame error

- The draft says "The constants 16 px and 0.2 are the frozen 8 px and 0.2 scaled to a two-frame interval. No new
  threshold is introduced." That statement holds only under one of two defensible scalings, and the draft does not
  say which one it uses or why.
- **Scaling (a), the draft:** band = max(16, 0.2 x |median S|). This scales the band with the length of the interval.
  - The 16 px follows from the triangle inequality: if each of two single-frame deviations is at most 8 px, their
    sum is at most 16 px.
  - The 0.2 is unchanged because 0.2 x |median S| is about 2 x (0.2 x |m|), where m is the single-frame median. So
    the whole band is about twice the frozen single-frame band.
- **Consequence of (a).** An isolated estimation error e at frame t enters S_t in full, not halved. Under (a) it is
  flagged only if |e| exceeds about 0.2 x |median S|. That is about 47 px in G1 (the frozen rule flags about 24 px)
  and 16 px in G4 (frozen: 8 px). M1-(a) is therefore **half as sensitive to isolated estimation errors** as the
  frozen rule. Catching such errors is the band's stated purpose.
- **Expected calibration effect, from arithmetic only.** In F4, half the injected failures are uniform on
  (-400, 400):
  - frozen rule: about 47/800 = 5.9% of them fall inside its band;
  - M1-(a): about 94/800 = 11.8% fall inside its band.

  Alias failures are caught by both. Expected F4 failure detection is therefore about 97% (frozen) against about
  94% (M1-(a)). The draft's "no regression within 1 percentage point" would very likely fail by construction,
  provided that criterion covers failure detection (the draft does not say).
- **Scaling (b):** band = max(8, 0.2 x |median S| / 2).
  - It keeps both frozen constants numerically.
  - It keeps the frozen sensitivity to an isolated single-frame error.
  - It still absorbs the alternation, because the alternation cancels in S rather than being tolerated by a wider
    band.
- Choosing between (a) and (b) is a methodological decision that only you can make. It must be fixed before the
  hash. My recommendation is (b), because it is the one that changes only what the band is applied to, not how much
  it tolerates. Whichever is chosen, the record must say the choice was made after this analytic audit and before
  any evaluation.

### B3. The synthetic calibration is underspecified, and one criterion fails by construction

- **Event adjacency.** Under M1 an event at frame t (failure, drop or duplicate) also changes S_(t+1). In F6,
  2% doubled and 1% tripled frames make about 3% of the following frames inconsistent under M1. Those frames are not
  events themselves, so "at least 99% of frames without an injected event are consistent" fails by construction
  unless the set of event-affected frames is defined as {t, t + 1}.
- **Not defined:**
  - the family index in the seed (F1 to F6 as 1 to 6?);
  - the order of random draws;
  - dy and r of synthetic frames;
  - whether failures replace the noisy value or are added to it;
  - what "doubled" means under alternation (F3);
  - the base value for aliases in F5 (constant -118 or the alternating value);
  - warm-up frames;
  - pooling across the 200 replicates;
  - which quantity "no regression" compares;
  - whether item 4 (Stage 3 reliability) is calibrated at all. The draft calibrates only the tau_r consistency
    flag, yet item 4 changes too.
- **Not stated:** that the frozen rule is computed by the existing, unchanged Stage 1 function on the identical
  arrays.

### B4. The AT-06b fallback is not fully deterministic

"Scan I192 then I193 ... if none, take the first 200 reliable frames in that order" leaves these points open:

- runs crossing the scenario boundary;
- what happens with fewer than 200 reliable frames in total;
- the pair definition when t - 1 is not reliable;
- the case of no column valid for both U and -U;
- ties in MSE;
- which motion rule produces the statuses;
- the access purpose for reading I192 and I193 images;
- that selection must be fixed and recorded before any image is read.

### B5. The AT-03 fallback bound is mathematically incomplete

- The expansion d = ||q||^2 + ||b||^2 - 2 q.b has three inner products. The standard bound (Higham, inner product
  of length n in floating point: |fl(x.y) - x.y| <= gamma_n |x|.|y|) gives, for the computed value d^(q, b):

  |d^(q, b) - d(q, b)| <= gamma_1026 (||q||^2 + ||b||^2 + 2 |q|.|b|)

  The draft omits the cross term 2 |q|.|b|, so its bound is too tight by up to a factor of 2.
  - n = 1,026 is the 1,024 products of each inner product plus the two additions that combine the terms.
  - Multiplying by 2 is exact.
  - The clamp at 0 can only reduce the error.
- The detector reports a minimum over b. If the float32 argmin b^ differs from the float64 argmin b*, the error of
  the minimum is bounded by the larger of the two pairwise bounds, not by the bound at b* alone:
  - min d^ <= d^(b*) <= d(b*) + E(b*);
  - min d^ = d^(b^) >= d(b^) - E(b^) >= d(b*) - E(b^).
- The float64 reference is not exact either. Its relative error is at most about 1,024 x 2^-53, which is negligible
  but should be stated.
- The bound needs TF32 off (already asserted in the run) and holds for any summation order, so tiled GPU matrix
  products and fused multiply-add are covered.

### B6. Stage 2 rerun sequencing is ambiguous

- Section 5 computes tau_r twice: offline from the run 1 motion files, and again in the Kaggle rerun. It does not
  say which one is the record. Two looks at the same quantity is exactly the "inspect, then decide" moment the
  protocol is meant to avoid.
- The protocol is also missing:
  - a new configuration file (the constants live in `pilot_v1_2_1.yaml`, whose hash is frozen);
  - a new Stage 1 record;
  - what happens if AT-06b or AT-03 fails again after the amendment.

## B. Non-blocking issues

- N1. Section 1 says "three specification problems" and lists four.
- N2. "(the AT-04c map tolerance)" is not a typo. AT-04c exists (section 23, line 706; Stage 3 start, maps
  rel <= 1e-4, mu0 and tau_cell relative difference <= 1e-4). The draft borrows its tolerance value for AT-04b's map
  part. AT-04c itself is unchanged. The wording should say so.
- N3. AT-06b may fail again on I192/I193. They run at the same speed as the aliased I199 (about 86 px per frame), and
  8 x 8 block means may hide their texture too. Their phase-correlation estimates are clean (IQR 4 px), which
  suggests otherwise, but the block-mean images were never checked. The consequence of a second failure must be
  pre-declared (see B6).
- N4. Under M1's item 4, the frame after a frame whose raw estimate fails the basic checks is no longer reliable. The
  number of held frames rises. This should be stated as a consequence, not discovered later.
- N5. M1 indirectly changes every quantity built on statuses: k_t (which frames count as reliable), oracle dx
  (section 7 item 9), motion-unknown frames (item 7), the V4 fallback and C0c. The protocol should list these.
- N6. AT-04b's new map tolerance (1e-4) is about 10 times above the smoke maximum (1.1e-5). With full coresets the
  nearest distances shrink, so the amplification grows. I expect it to stay below 1e-4, but this is not verified.
- N7. "The camera's alternating frame interval" is an interpretation of the traces, not an established fact. It
  should be phrased as the most likely explanation.

## C. Verified parts

- AT-04c exists, and the borrowed value 1e-4 is its map tolerance.
- The feature part of the new AT-04b (rel <= 1e-6) matches the preregistration's own expectation (section 6, "Batch"
  row: "about 1e-7"). The smoke features met it (2.4e-7).
- gamma_1026 = 1026 u / (1 - 1026 u) with u = 2^-24 is 6.1158e-5, as stated. u = 2^-24 is the unit roundoff of IEEE
  float32 with round-to-nearest.
- d32 and d64 are both squared Euclidean distances. d32 is the pipeline value (`scoring.nearest_sq_dist`). d64 is
  the float64 brute force sum of (q - b)^2 in `acceptance2.at03`. b* is the float64 nearest neighbour.
- Feature scaling does not change the bound. Both sides are homogeneous of degree 2 in (q, b), so scaling the
  features scales both sides equally. The features are non-negative (ReLU outputs, averaged and bilinearly
  interpolated), so |q|.|b| = q.b. The bound is written with |q|.|b| anyway so that it needs no assumption.
- The fallback concerns AT-03 acceptance only. The detector distance computation is not changed.
- M1 is a single candidate. Failure of the calibration leaves the frozen rule and A-G4 motion-invalid.
- Everything outside section 7 items 3 and 4 and the three tests is unchanged.

## D. Exact text changes required (proposed; to be applied only on your instruction)

### D1. Replace the Status paragraph and add a status section before section 1

> Status: draft for review. Nothing in sections 3 and 4 has been evaluated on any data. On approval, this text's
> SHA-256 is recorded in the decision log before any calibration or real-data computation.
>
> **Nature of this amendment.** v1.2.2 is a post-Stage-2 diagnostic amendment. It was written after Stage 2 run 1
> failed, and its motion rule M1 was designed after viewing label-free phase-correlation traces from that run. M1 is
> not part of the preregistration of 2026-09-27 or of amendment v1.2.1, and must never be described as
> preregistered. What is pre-declared is this protocol: one candidate, fixed calibration criteria, and acceptance of
> whatever the single real-data evaluation produces. The text was revised after an analytic audit (no runs) on
> 2026-10-07.

### D2. Section 1: "three specification problems" becomes "four specification problems".

### D3. Section 2: replace the third bullet by

> - Viewed and used to design M1 (real data, label-free):
>   - the median and IQR of the two-frame sum S_t = dx_t + dx_(t-1) on T1_S174_I111_1 (-247.7, 10.5),
>     T1_S148_I108_2 (-248.6, 14.7), T1_S478_I118_1 (-79.1, 5.0) and T1_S164_I199_1 (-169.1, 184.0);
>   - lag-1 correlations of single-frame deviations;
>   - the frozen rule's per-scenario consistency;
>   - a classification of its inconsistent pairs by size of deviation.
>
>   The first three scenarios are test scenarios of A-G1 or A-G4, seen only as training-side motion. M1's
>   consistency flags and tau_r were not computed on real data.
> - Viewed: the 200 AT-06b pairs (shifts and MSEs) on T1_S164_I199_1, validation data.
> - No test-scenario label, anomaly map, detector score or metric was computed or viewed. The only detector outputs
>   seen are validation-frame numbers from the smoke run (AT-02, AT-03, AT-04a, AT-04b).

### D4. Section 3, C1: replace the item 3 and item 4 bullets and the "Why two frames" bullet by

> Definitions. For a frame t with an estimate (has_est) whose predecessor t - 1 also has one,
> S_t = dx_t + dx_(t-1), using raw single-frame estimates. S_t is undefined otherwise.
>
> - **Item 3 (tau_r consistency).** The history H3 of a scenario is the list of every defined S_j, j < t, in time
>   order, regardless of r, bounds or consistency. Pair t is consistent iff |dx_t| <= 400 and |dy_t| <= 16 and, if
>   S_t is defined and H3 has at least 5 entries, |S_t - median(last up to 15 entries of H3)| <= B(median). If S_t
>   is undefined, or H3 has fewer than 5 entries, only the two bound checks apply.
> - **Item 4 (reliable at t).** Frame t is reliable iff r_t >= tau_r, |dx_t| <= 400, |dy_t| <= 16, frame t - 1 has
>   an estimate with r_(t-1) >= tau_r, |dx_(t-1)| <= 400 and |dy_(t-1)| <= 16, and, if the reliable history H4 (S_j
>   of every earlier reliable frame j, in time order) has at least 5 entries,
>   |S_t - median(last up to 15 entries of H4)| <= B(median). Held and unknown statuses, and their 5-frame rule, are
>   unchanged.
> - **Band B.** [Choose one before hashing.]
>   - (a) B(M) = max(16, 0.2 x |M|): the frozen band scaled to a two-frame interval. It tolerates isolated
>     single-frame errors about twice as large as the frozen rule does.
>   - (b) B(M) = max(8, 0.2 x |M| / 2): the frozen band, in single-frame units, applied to the two-frame sum. It keeps
>     the frozen sensitivity to isolated errors.
> - Medians use numpy's median (mean of the two middle values for an even count). Comparisons are inclusive (<=), as
>   in the frozen rule.
> - Unchanged: U(t, i) from single-frame dx; k_t and m_t from single-frame |dx| of reliable frames; held dx = last
>   reliable dx.
> - Changed indirectly, through the statuses: the reliable set used by k_t, oracle dx, motion-unknown frames, the
>   V4-family fallback, and C0c.
> - Rationale: the most likely explanation of the G1 traces is an alternating frame interval. The single-frame
>   displacement then alternates while the two-frame sum stays nearly constant. Testing S_t lets genuine alternation
>   pass while still flagging isolated errors.
> - Known costs: a duplicated or dropped frame at t makes S_t and S_(t+1) inconsistent. The frame after a frame
>   whose raw estimate fails the basic checks is not reliable.

### D5. Section 3, C2: replace by

> **C2. AT-04b.** Validation frames 1 to 10, computed once with batch size 1 and once with batch size 4 (batches
> {1-4}, {5-8}, {9-10}). Both parts are required:
>
> - features (10 x 8,000 x 1,024): max|f1 - f4| / max|f4| <= 1e-6;
> - maps under each of the six coresets: max|a1 - a4| / max|a4| <= 1e-4.
>
> The map tolerance reuses the value of AT-04c's map criterion. AT-04c itself (start of Stage 3) is unchanged.

### D6. Section 3, C3: replace the fallback sentence by

> Fallback, applied only if the primary criterion fails. For each of the 2,000 queries q:
>
> - b* is the smallest-index float64 minimiser;
> - b^ is the coreset vector the float32 computation returned;
> - E(b) = gamma_1026 (||q||^2 + ||b||^2 + 2 |q|.|b|) + 1,024 x 2^-53 x d64(q, b*), all evaluated in float64.
>
> The query passes iff |d32(q) - d64(q)| <= max(E(b*), E(b^)). The fallback passes iff every query passes.
> gamma_n = n u / (1 - n u), u = 2^-24, n = 1,026: 1,024 products per inner product plus the two additions combining
> ||q||^2, ||b||^2 and -2 q.b.
>
> AT-03 = PASS if the primary or, failing that, the fallback passes. Both results are recorded. This changes only
> AT-03's acceptance; the detector's distance computation is unchanged.

### D7. Section 3, C4: replace the procedure by

> Statuses of T1_S164_I192_1 and T1_S164_I193_1 are computed under the fold's tau_r with the motion rule in force
> (M1 if adopted, else the frozen rule). Pairs are (t - 1, t) with frame t reliable, 1-based; frame t - 1 may have
> any status. U(t, 1) = floor(-dx_t / 8 + 0.5).
>
> Selection is made from statuses alone, written to the record with its hash, and fixed **before** any image is
> read:
>
> 1. the earliest run of 200 consecutive reliable frames in I192;
> 2. else the earliest such run in I193 (runs never cross scenarios);
> 3. else the first 200 reliable frames of I192 in time order, continued with those of I193 only after I192's are
>    exhausted;
> 4. if I192 and I193 together have fewer than 200 reliable frames, AT-06b = FAIL for that fold.
>
> Images are read under purpose `motion` (both scenarios are training-side in both folds) and are never passed to
> the detector. A pair holds iff the U-warp MSE is strictly smaller than the -U-warp MSE on the columns valid for
> both. If no column is valid for both, the pair does not hold. Pass iff at least 190 of 200 pairs hold. The MSE at
> zero shift is reported, not gated. If tau_r is undefined for a fold, AT-06b is not applicable to it.

### D8. Section 4: replace the calibration paragraph and criteria by

> **Generation.**
>
> - Families F1 to F6 have indices 1 to 6. Replicate r = 0..199 uses
>   `rng = numpy.random.default_rng([20261007, family_index, r])`.
> - Each trace has 2,000 frames. Frame 1 has no estimate; frames 2 to 2,000 have one, with r_t = 1 and dy_t = 0.
> - Draws, in this order, each as one vectorised call of length 2,000:
>   - noise = `rng.normal(0, 2, 2000)`;
>   - u = `rng.random(2000)`;
>   - w = `rng.uniform(-400, 400, 2000)`;
>   - k = `rng.choice([-2, -1, 1, 2], 2000)`.
> - Base displacement b_t:
>   - F1, F4: -118;
>   - F2, F3, F5: -117 at even t, -140 at odd t;
>   - F6: -39.
> - True displacement:
>   - F3 and F6 events: doubled when u_t < 0.01 (F6: 0.02), giving 2 b_t; tripled in F6 when 0.02 <= u_t < 0.03,
>     giving 3 b_t; duplicated in F3 when 0.01 <= u_t < 0.015, giving 0;
>   - otherwise b_t.
> - Estimate dx_t = true displacement + noise_t, except in F4 and F5:
>   - failure "uniform" when u_t < 0.05: dx_t = w_t;
>   - failure "alias" when 0.05 <= u_t < 0.10: dx_t = b_t + 85 k_t;
>   - failures replace the estimate, with no noise added.
>
> **Sets.**
>
> - Event frames are the frames given an injected drop, duplicate or failure.
> - Affected frames are each event frame t and t + 1.
> - Clean frames are frames 21 to 2,000 that are not affected. Frames 2 to 20 are warm-up and excluded for both
>   rules.
>
> **Rules compared.**
>
> - The frozen rule is computed by the unchanged Stage 1 function `motion.tau_r` (consistency part) and
>   `motion.statuses` (with tau_r = 0).
> - M1 is computed by the new functions.
> - Both are computed on the identical arrays.
> - "Consistent" is the item 3 flag; "reliable" is the item 4 status with tau_r = 0.
> - Proportions are pooled over the 200 replicates of a family.
>
> **Criteria (all required, item 3 and item 4 each):**
>
> 1. F1, F2, F6: at least 99% of clean frames consistent (reliable).
> 2. F4, F5: at least 90% of event frames inconsistent (not reliable).
> 3. F1 and F4: M1's clean-frame acceptance is no more than 1 percentage point below the frozen rule's. M1's
>    event-frame detection in F4 is no more than 1 percentage point below the frozen rule's.
>
> F3 is reported, not gated.

### D9. Section 5: replace by

> If M1 passes section 4:
>
> 1. A new configuration file `configs/pilot_v1_2_2.yaml` records M1's band and the AT changes. Its hash, and this
>    protocol's hash, are logged.
> 2. `motion.py` gains the M1 functions. The frozen functions stay, for the comparison and the record.
> 3. The full Stage 1 suite is rerun on Kaggle as a new Stage 1 record for v1.2.2.
> 4. Stage 2 is rerun from the beginning on Kaggle. Its phase A computes tau_r per fold from its own motion
>    estimates. That value is the only tau_r of record, and it is final, including "undefined". No offline
>    computation of tau_r under M1 is made from the run 1 files. The rerun's motion files are compared with run 1's
>    by hash and the comparison is reported.
>
> No detector output is used in any step. If M1 fails section 4, the frozen rule stays: A-G4 is motion-invalid and
> steps 1 to 4 proceed with the frozen rule and the C2 to C4 changes.
>
> **No further amendments of section 7, AT-03, AT-04b or AT-06b are permitted in this pilot.** If any of them fails
> after v1.2.2, Stage 3 does not start. The pilot is then reported as stopped at Stage 2, with the failure recorded.

## E. Verdict

**NOT READY.** Six blockers remain:

1. incomplete disclosure (B1);
2. an undeclared choice of band scaling (B2), which needs your decision;
3. calibration definitions, including one criterion that fails by construction (B3);
4. the AT-06b selection rule (B4);
5. the AT-03 bound (B5);
6. the sequencing of the rerun (B6).

All six are wording fixes; none needs data. Once you choose band (a) or (b) and approve the D1 to D9 changes, the
corrected draft can be hashed.
