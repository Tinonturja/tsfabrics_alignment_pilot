---
title: "TSFabrics Research Gate v1.2: Pre-Implementation Specification"
subtitle: "Proposed frozen pre-registration for the alignment pilot, with a fresh adversarial audit (2026-09-27). Supersedes v1.1."
author: "Prepared for Tinon Turja Majumder"
date: "2026-09-27"
---

# 1. Executive summary

**What v1.2 is.** v1.2 is the pre-registration for a two-fold GPU pilot on TSFabrics. The pilot asks whether averaging anomaly evidence at corresponding physical fabric locations (V4) changes false alarms and missed defects. It compares V4 with:

- frame-independent scoring (V0);
- ordinary temporal averaging (V1, V2);
- two deliberately wrong-correspondence controls (V4-reverse, V4-lagperm).

**What changed from v1.1.** All nine blockers of the final v1.1 audit are addressed. Four of the requested fixes changed once I tested them:

1. **B6, bootstrap.** 1,200-frame blocks are **not** sufficient. No contiguous block length fixes the dependence, because it is periodic, not short-range. In simulation with recurring fabric-fixed false-alarm sources:
   - 600-, 1,200- and 2,400-frame blocks recovered only 26% to 41% of the true standard error;
   - rotation-phase clusters anchored on cutline runs recovered 78% to 91%.
   
   v1.2 therefore uses phase clusters, with 1,200-frame blocks as a second scheme. The decision takes the lower of the two confidence bounds.
2. **B8, chance baseline.** Circular shifts are restricted to offsets whose rotation phase is at least a quarter-rotation away from zero. This stops a shifted trace from realigning recurring defects.
3. **B1, event cap.** The cap D = 25 was tested against D = 50. D = 50 lets a slowly drifting score recover more P3 (0.16 to 0.19 against 0.11 to 0.13), so D = 25 stays.
4. **B7, C6.** It is repaired and passes the synthetic tests. It still rests on unvalidated constants and has known blind spots, so it is **demoted to exploratory**. It plays no role in any decision.

**Additional gaps found while writing v1.2, now resolved in this document:**

- whether validation constants are recomputed for coreset seeds 1 and 2 (they are);
- how Stage 3 verifies the Stage 2 constants;
- the exact carry-over rule for the passes that follow another pass closely;
- the A-G4 validation overlap (resolved by moving T1_S164_I199_1 from A-G4's bank into A-G4's validation role).

**Verdict of the fresh audit (section 31).** The fresh audit of my first draft found 11 specification defects: one self-contradiction in the staging rules, and ten underspecified details. All were corrected in this text before freezing; they are listed in section 31. After that: **READY FOR CODING.** Ten non-blocking limitations must be carried into the report. Two of them deserve attention before anyone reads a result:

- In A-G1 the three largest candidate tracks hold 57% of the passes.
- Even the repaired bootstrap under-covers in A-G1 (about 0.8 of the true standard error in simulation).

Neither is an ambiguity, a leakage path or a free implementation choice, but both limit how strongly an A outcome can be read.

**Verification done for v1.2.** No TSFabrics image or score was used. The reference and audit scripts are in `gate_v12_reference/`:

| Script | Result |
|---|---|
| `test_ref_metrics.py` | 14 hand-computed tests of the event rule, P1, P2 and P3 in exact rational arithmetic: all pass. The union-find sweep matches the direct definition in 1,500 random cases |
| `audit_b1_metric.py` | Section 12 evidence |
| `audit_b6_bootstrap.py`, `audit_b6_phase_est.py` | Section 18 evidence |
| `audit_b8_chance.py` | Section 19 evidence |
| `audit_b7_c6.py` | Section 16 evidence |
| `audit_decision_enum.py` | 3,329,778,253,824 two-fold primitive states: 0 invariant violations, and exactly one closed-form outcome per state |
| `ref_bank_quota.py` | Reproduces the frozen v1.1 quotas and derives the v1.2 A-G4 change |

# 2. Scientific question

> In normal-only memory-bank anomaly detection on video of knitted fabric translating past a fixed camera: when the same per-frame anomaly maps and the same temporal window are used, does combining evidence at corresponding physical fabric locations change false-alarm and missed-defect rates? The comparison is against frame-independent scoring, ordinary temporal score and map averaging, and deliberately wrong correspondence controls.

**Changes from v1.1 and exclusions:**

- The second clause of v1.1's question ("are the remaining false alarms transient, persistent or global?") is removed from the confirmatory question. It is exploratory now (section 16).
- **No methodological novelty is claimed** for motion-compensated aggregation (shift-and-add).
- The following are excluded:
  - open-set or cross-texture generalization;
  - early defect prediction;
  - multi-class segmentation;
  - cross-factory generalization;
  - any real-time superiority claim.

# 3. Dataset and forensic facts

All facts come from the forensic audit (`claude/tsfabrics-forensic-audit-2026-09-24.md`) and the frozen CSVs. None are re-derived here.

| Fact | Value |
|---|---|
| Frames | 93,196 JPEG, 800 x 640, grayscale |
| Scenarios; condition groups; clusters; textures | 22; G1 to G8; C1 to C11 (clusters stay intact across splits); T1, T2, T3 |
| Pure-normal frames; defect frames | 37,732; 3,296 |
| Strict defect episodes (passes) | 268 in total; 261 in the two pilot folds |
| Candidate recurrence tracks | about 77 (an upper bound, not confirmed identities); 70 in the pilot folds |
| Label 4 | Most of the defect-frame mass |
| Label 5 | Coincides with cutline passes. It is not an independent defect category. In the pilot folds it occurs only together with label 4 (10 passes labelled [4, 5]); no pass is label-5-only |
| Label 2 (cutline) | Normal |
| Fabric displacement | 38 to 161 px/frame where measurable. Every pilot test scenario moves left |
| Phase correlation | Fails in 3 dark scenarios, none of which is a pilot test scenario |
| Rotation periods (frames), from cutline recurrence | S148_I108_1 153; S148_I108_2 156; S174_I108_1 59; S174_I111_1 176; S177_I108_1 176; S478_I118_1 477; S478_I118_2 487; S555_I117_1 556; S164_I199_1 171 |
| Frame-random splitting | Invalid. Condition-group-disjoint evaluation is required |

# 4. Fold design

**Test sets are unchanged from v1.1.**

| Fold | Test group | Test scenarios | Test frames | Passes | Tracks |
|---|---|---|---:|---:|---:|
| A-G1 | G1 | T1_S148_I108_1, T1_S148_I108_2, T1_S174_I108_1, T1_S174_I111_1, T1_S177_I108_1 | 43,744 | 162 | 34 |
| A-G4 | G4 | T1_S478_I118_1, T1_S478_I118_2, T1_S555_I117_1 | 24,916 | 99 | 36 |

**Validation is changed for A-G4 (CL-02).**

| Fold | Validation (training side, never in the bank) | Bank sources |
|---|---|---|
| A-G1 | T1_S164_I199_1, frames 1 to 1,212 (all) | unchanged: G2 {I192, I193}, G3 {I36, I35}, G4 {S478_1, S478_2, S555} |
| A-G4 | **T1_S164_I199_1, frames 1 to 1,212 (all)** | G1 {S148_1, S148_2, S174_I108_1, S174_I111_1}, **G2 {I192, I193}**, G3 {I36, I35} |

**Why the A-G4 validation had to change.**

- In v1.1, A-G4's validation used frames 1 to 3,000 of T1_S177_I108_1. That is an A-G1 test scenario with no defects, and it supplies 16,431 of A-G1's roughly 41,800 normal evaluation frames (39%).
- Statistically, cross-fold reuse of training-side data is normal in leave-one-group-out designs. Every bank already contains the other fold's test scenarios.
- **Validation is different from the bank.** It is where the researcher is allowed to **look at detector outputs** during development (Stage 2). Inspecting maps and false-alarm behaviour on an A-G1 test scenario before A-G1 is scored is a blinding breach, not a statistical one.
- So v1.2 moves the only G2 scenario that is not a bank source in A-G1 (T1_S164_I199_1) out of A-G4's bank and into A-G4's validation role. **No validation scenario is now a test scenario in either fold.** Both folds validate on the same scenario, which is a test scenario nowhere.

**Frozen bank quotas, v1.2.** A-G1 is identical to v1.1. For A-G4, G2 is re-allocated by the unchanged water-fill rule (verified by `ref_bank_quota.py`, which also reproduces every v1.1 quota).

| Fold | Scenario | Group | Margin | Spacing | Eligible | Capacity | Quota v1.1 | **Quota v1.2** |
|---|---|---|---:|---:|---:|---:|---:|---:|
| A-G4 | T1_S148_I108_1 | G1 | 13 | 8 | 876 | 127 | 31 | 31 |
| A-G4 | T1_S148_I108_2 | G1 | 12 | 7 | 3,894 | 571 | 31 | 31 |
| A-G4 | T1_S174_I108_1 | G1 | 12 | 7 | 45 | 7 | 7 | 7 |
| A-G4 | T1_S174_I111_1 | G1 | 12 | 7 | 18,600 | 2,658 | 31 | 31 |
| A-G4 | T1_S164_I192_1 | G2 | 15 | 10 | 952 | 96 | 34 | **50** |
| A-G4 | T1_S164_I193_1 | G2 | 15 | 10 | 997 | 101 | 33 | **50** |
| A-G4 | T1_S164_I199_1 | G2 | n/a | n/a | n/a | n/a | 33 | **0 (validation)** |
| A-G4 | T1_S164_I36_1 | G3 | n/a | 20 | 1,807 | 91 | 50 | 50 |
| A-G4 | T1_S179_I35_1 | G3 | n/a | 20 | 1,807 | 91 | 50 | 50 |

- The eligibility, capacity-list and selection rules are unchanged from v1.1 section A6:
  - eligible = label in {1, 2}, and |f - d| > margin for every defect frame d;
  - capacity list by greedy spacing;
  - selection C[floor((j + 0.5) c / q)].
- Each fold totals 300 frames.
- The sets are pairwise disjoint within each fold: bank, validation and test.
- The A-G4 validation set shrinks from 3,000 to 1,212 frames. Every validation constant is still estimated from at least 9.6 million cells. The deployment table (a diagnostic) becomes coarser.

**tau_r source (unchanged, stated precisely):** every scenario of the fold's training-side groups, full length, label-free.

- A-G1: G2, G3 and G4 scenarios.
- A-G4: G1, G2 and G3 scenarios, including T1_S177_I108_1.

This uses only phase-correlation output, never detector output, so it does not breach blinding.

# 5. Data leakage rules

1. No test-scenario label, mask, pass, track, score or map may influence any of the following: the detector, the bank, the coreset, a validation constant, tau_r, k, a threshold, a variant, a control, a criterion or a decision rule.
2. Test labels are used **only** to define the evaluation units: passes, windows, N_f, tracks, and the resampling clusters of section 18, which are anchored on label-2 and label-5 runs.
3. Detector outputs on test scenarios exist only in Stage 3 (section 24).
4. Every constant chosen with knowledge of whole-dataset descriptive statistics is disclosed in section 29.
5. Validation outputs may be inspected in Stage 2. No validation scenario is a test scenario in either fold.

# 6. PatchCore-derived detector

**Name.** "PatchCore-derived normal-memory anomaly detector". It follows the official `amazon-science/patchcore-inspection` feature, coreset and scoring path, **pinned to commit `fcaa92f`** (2023-03-06), with deviations D1 to D7. It is **not** called canonical PatchCore anywhere.

| Item | Frozen setting | Relation to the official code |
|---|---|---|
| Backbone | torchvision `wide_resnet50_2`, weights `IMAGENET1K_V1`, eval mode, no gradients | Same |
| Decoding | `cv2.imread(path, cv2.IMREAD_GRAYSCALE)` to uint8 [640, 800] | **D2:** gray input |
| Input | float32 / 255, replicated to 3 channels, ImageNet mean (0.485, 0.456, 0.406) and std (0.229, 0.224, 0.225); shape (B, 3, 640, 800) | **D1:** no resize or crop (official: resize 256, crop 224). The effective object scale changes by about 3.6x |
| Layers | Hooks on `layer2` (512 x 80 x 100) and `layer3` (1024 x 40 x 50) | Same |
| Patches | `torch.nn.Unfold(3, stride=1, padding=1)`. Output channel order is (c, ki, kj), c outermost | Same as the official flatten order (C, 3, 3) |
| Per-layer projection | Reshape to (N, 1, C x 9), `adaptive_avg_pool1d` to 1024 (MeanMapper) | Same |
| Layer-3 alignment | MeanMapper on the 40 x 50 grid, **then** bilinear (`align_corners=False`) to 80 x 100 | **D4:** order swapped. Both are linear maps on different axes; exactness is checked by AT-02 |
| Aggregation | Stack to (N, 2, 1024), reshape (N, 1, 2048), `adaptive_avg_pool1d` to 1024 | Same |
| Layout | (8,000 x 1,024) per frame, row-major, index = 100 r + c | Same |
| Bank | 300 frames per fold (section 4) | **D7:** pooled multi-scenario sample |
| Coreset | `ApproximateGreedyCoresetSampler(percentage=0.01, number_of_starting_points=10, dimension_to_project_features_to=128)` gives 24,000 vectors. `_reduce_features` is replaced by a row-chunked equivalent (chunks of 100,000 rows, the same `Linear` weights), on CUDA. Input order: groups ascending, scenarios lexicographic, frames ascending, cells row-major | Same class and parameters. **D5:** chunked projection |
| Seeding | Immediately before `sampler.run`: `random.seed(s)`, `np.random.seed(s)`, `torch.manual_seed(s)`, `torch.cuda.manual_seed_all(s)`. Globally `cudnn.deterministic=True`, `benchmark=False`, `allow_tf32=False` | **Differs from the official `fix_seeds`**, which seeds the same generators at the start of a run and before backbone loading and does not set cuDNN flags. So seed s here does not reproduce the official run's seed s |
| Coreset seeds | s = 0 (primary), 1 and 2 (follow-up). All three coresets are built in Stage 2, saved (indices and vectors) and hashed. Stage 3 loads them and never rebuilds a coreset | Implementation choice, frozen |
| Distance | **Squared L2**, exact 1-NN over the coreset: max(0, \|\|q\|\|^2 + \|\|b\|\|^2 - 2 q.b) in fp32, queries in chunks of 2,000 | Same metric as `faiss.IndexFlatL2`. **D6:** torch instead of faiss |
| Patch score | a_t(r, c) = min_b d2(f_t(r, c), b) | Same (n_nn = 1) |
| Frame score | s_t = max over (r, c) of a_t | Same as the official code, which does not implement the reweighting described in the paper (the paper's equation must be re-checked before citing) |
| Map | Raw (80, 100) float32; no upsampling; no blur | **D3** |
| Batch | 4 frames; eval-mode BatchNorm | Numerically batch-sensitive at about 1e-7 only (AT-04b) |

# 7. Motion estimation

This section is unchanged from v1.1 section A7 and repeated here for completeness.

1. **Crop and standardise.** Rows 32 to 607 (576 x 800), float32. Standardise by crop mean and population standard deviation. A frame with std < 1e-6 has no estimate.
2. **Estimate.** `(dx, dy), r = cv2.phaseCorrelate(P.copy(), C.copy(), W)`.
   - P is frame t-1, C is frame t, and W = `createHanningWindow((800, 576), CV_32F)`.
   - The copies are mandatory.
   - Sign convention: I_t(x) = I_(t-1)(x - dx_t), so leftward motion gives dx < 0.
3. **tau_r.** Smallest value on the grid {0.00, 0.01, ..., 1.00} for which at least 1,000 training-side pairs have r >= tau and at least 95% of those pairs are consistent.
   - Consistent means: |dx| <= 400, |dy| <= 16, and, once at least 5 earlier pairs exist in the scenario, |dx - median(previous up to 15 pairs, any r)| <= max(8, 0.2 x |that median|).
   - If no grid value qualifies, the fold is motion-invalid.
4. **Reliable at t:** r_t >= tau_r, |dx| <= 400 and |dy| <= 16. Once at least 5 earlier reliable estimates exist: |dx_t - median(last up to 15 reliable dx)| <= max(8, 0.2 x |median|).
5. **Status of every frame:**
   - `reliable`;
   - `held` (unreliable, but t - last reliable <= 5; takes the last reliable dx);
   - `unknown` (everything else). Frame 1 is always unknown.
6. **Cells.** u_j = dx_j / 8 (float64). U(t, i) = floor(-(u_(t-i+1) + ... + u_t) + 0.5), with U(t, 0) = 0.
7. **Motion-unknown frame:** any j in [t - K + 2, t] with status `unknown`.
8. **C0c (motion-invalid):** tau_r is undefined, or more than 5% of the fold's test frames are motion-unknown.
9. **Oracle dx (diagnostic only):** the median of reliable dx over [j - 15, j + 15], requiring at least 5 values.

# 8. Temporal aggregation

- m_t = median |dx| of the last up to 15 **reliable** estimates at or before t (numpy median; for an even count, the mean of the two middle values).
- **Adaptive window:**
  - k_t = 10 if fewer than 5 reliable estimates exist so far;
  - k_t = 25 if m_t = 0 (new in v1.2: fabric stopped);
  - otherwise k_t = min(25, max(3, floor(800 / m_t + 0.5))).
- K_t = min(k_t, t), where t is the 1-based frame index within the scenario. This applies to every variant.
- All temporal sums (scores for V1, maps for V2 to V4-oracle) are accumulated in **float64** and divided by K. Maps are then cast to float32 before the spatial max. This makes the identity tests in AT-07 exact.
- **Fallback:** at motion-unknown frames, V4, V4-reverse and V4-lagperm output V2's value. V4-oracle does the same at its own oracle-unknown frames. The motion-unknown fraction is reported.
- **Per-seed constants (new, CL-12).** mu0, b1, b3, tau_cell and the deployment thresholds depend on the detector. They are recomputed from each coreset seed's own validation maps. Stage 2 saves them per seed; Stage 3 recomputes and verifies them (AT-04c).

# 9. Variant definitions

**Common definitions:**

- lags i = 0 .. K-1;
- mu0 = mean of a_t(r, c) over all cells of all validation frames (per fold and seed);
- valid(x, U) = [0 <= x + U <= 99];
- W(A, U)(r, x) = A(r, x + U) if valid, else mu0.

| Variant | Frame score | Role | Causal |
|---|---|---|---|
| V0 | s_t | Baseline; used in C0 | Yes |
| V1 | (1/K) sum_i s_(t-i) | **Primary comparator** (temporal score smoothing) | Yes |
| V2 | max over (r, x) of (1/K) sum_i a_(t-i)(r, x) | **Control C-V2** (unaligned map averaging) | Yes |
| V4 | max of (1/K) sum_i W(a_(t-i), U(t, i)) | **Tested arm** | Yes |
| V4-reverse | max of (1/K) sum_i W(a_(t-i), -U(t, i)) | **Control C-REV** | Yes |
| V4-lagperm | max of (1/K) sum_i W(a_(t-pi(i)), U(t, i)) | **Control C-LAG** | Yes |
| V4-oracle | V4 with oracle dx | Diagnostic (C5); not deployable; never decision-relevant | **No** |

**Lag permutation:** pi(0) = 0. For K >= 3, pi(i) = (i mod (K - 1)) + 1 for i >= 1. For K <= 2, pi is the identity. pi depends only on K.

# 10. Controls

**Roles.**

- V1 is the comparator that defines the gain: G = P3(V4) - P3(V1).
- **All three controls, C-V2, C-REV and C-LAG, are primary and decision-relevant**, and V4 must beat every one of them (section 21). There are no secondary controls.
- V4-oracle is a diagnostic.
- Each control answers a different alternative explanation:

| Control | Alternative explanation it tests | Matched with V4 | Not matched |
|---|---|---|---|
| C-V2 | The gain comes from averaging **maps** rather than scores, not from correspondence | Maps, K, frames | No warp, no prior-fill |
| C-REV | The gain does not depend on the **direction** of the pairing | Maps, K, displacement magnitudes, number of prior-filled cells | Which edge is filled; which side of each past map is read |
| C-LAG | The gain does not need each shift paired with the **correct past frame** | Maps, K, shifts, validity masks, prior-fill, source columns | Frame-to-shift pairing only |

**Proven properties of C-LAG (AT-08).** For K >= 3, pi is a single (K - 1)-cycle on {1..K-1} with no fixed point there, and pi(0) = 0. The multiset of source frames equals V4's. Term i reads the same columns x + U(t, i) with the same validity mask and the same prior-fill count. It is deterministic and causal (pi(i) <= K - 1).

**What C-LAG does not guarantee (correcting v1.1).**

- The misalignment of term i >= 1 is Delta_i = U(t, pi(i)) - U(t, i). For i < K - 1, a floor(x + 0.5) rounding of a difference w gives floor(w) or ceil(w), so **\|Delta_i\| >= floor(\|dx_(t-i)\| / 8) cells**. At the slowest measured speed (38 px/frame, u = 4.75) the minimum is **4 cells**, not 4.75.
- The misalignment **vanishes when the fabric barely moves**. With \|dx\| < 4 px, consecutive shifts coincide and C-LAG equals V4 on those terms. At a standstill, V4 = C-LAG = C-REV = V2.
- A defect wider than the misalignment partly overlaps its misaligned copy. This makes C-LAG look better, which is conservative with respect to outcome A.
- Declared equivalences with V4: frames 1 and 2 of each scenario (K <= 2), and motion-unknown frames (all three controls equal V2). The fraction of test frames where C-LAG equals V4 on at least one lag is reported.

**Proven property of C-REV.** Let M be the mirror x -> 99 - x. Then W(a, -U)(x) = W(Ma, U)(99 - x), and validity maps the same way. So **V4-reverse is exactly V4 applied to mirror-imaged maps** with the same shift sequence.

**Limitation of C-REV.** All eight test scenarios move left, so left-right spatial asymmetry in the maps is fully confounded with direction:

- V4 reads the upstream side of each past map and fills at the entry edge;
- C-REV reads the downstream side and fills at the exit edge.

C-REV is therefore never interpreted alone; it is informative only together with C-LAG, which reads V4's own columns. A label-free left-right profile (column means of b1 on validation frames) is reported in Stage 2, before any test scoring.

# 11. Pass-window definition

**The window of pass p** in scenario s is W_p = [s_p, min(g_p, s_next - 1, N_s)], where:

- g_p = max{ t in [e_p, min(e_p + 24, N_s)] : t - K_t + 1 <= e_p }. It always exists, because t = e_p qualifies;
- s_next is the next pass start in the same scenario;
- N_s is the scenario length.

**Verified properties.**

| Case | Behaviour |
|---|---|
| **Disjointness** | W_p ends before s_next, so no frame belongs to two windows and **no alarm frame can credit two passes** |
| Adjacent passes (s_next = e_p + 1) | W_p = [s_p, e_p]; no grace |
| Same-track passes | Separate windows and separate units. The track score z_k = max over its passes |
| Grace credit | Temporal variants legitimately see the defect in their causal window during the grace frames. V0 can gain noise credit there. This is identical across variants and is included in the chance baseline (section 19) |
| **Carry-over (evidence, not alarms)** | See below |

**Carry-over rule (frozen).** A pass p that is not the first in its scenario is *carry-over-affected* if s_p - K_(s_p) + 1 <= e_(p-1). That means the causal window at its first frame still contains the previous pass's last frame, so a temporal variant can score it using the previous pass's evidence.

- The exact set depends on K_t, which is known only in Stage 3 (label-free).
- An estimate using scenario-median k gives **24 of 162 (A-G1) and 10 of 99 (A-G4)**. Of these 34, 24 are in the same track as the previous pass.
- Primary analyses keep these passes. **Sensitivity S2** removes them from R_pass and R_track, drops any track left with no passes, and keeps windows and N_f unchanged. S2 is secondary and cannot change the decision.

**Normal evaluation set.** N_f = frames of the fold's test scenarios with label in {1, 2} that lie outside every W_p.

# 12. False-alarm event definition

**Definitions at threshold tau for variant v:**

1. **Alarm frame:** a frame t in N_f with S_v(t) >= tau.
2. **Excluded frame:** any frame not in N_f (a pass-window frame, which includes every defect frame).
3. **Link:** two alarm frames u < w of the same scenario are linked if w - u <= 3 and every frame strictly between them is in N_f. So a gap of at most 2 non-alarm **normal** frames merges; any excluded frame between them prevents merging; scenarios never merge.
4. **Run:** a connected component of the link relation. Its span is L = last - first + 1, counting the merged non-alarm frames inside it.
5. **Event count:** Count_v(tau) = sum over runs of ceil(L / 25).

| L | 1 | 25 | 26 | 50 | 51 | 75 | 76 |
|---|---|---|---|---|---|---|---|
| events | 1 | 1 | 2 | 2 | 3 | 3 | 4 |

6. **FA rate:**
   - FA_v(tau) = 1000 x Count_v(tau) / \|N_f\|, pooled over the fold.
   - FA_env,v(tau) = max over thresholds tau' >= tau in the grid of FA_v(tau').
7. **Bootstrap attribution:**
   - A run [a, b] is split into consecutive chunks starting at a, a + 25, a + 50, ....
   - Each chunk is one event, attributed to the resampling unit that contains its first frame.
   - Per-unit counts therefore sum exactly to Count_v(tau).

**Why 25.** It is the frozen upper bound of K. A run of at most 25 frames counts once in every variant, so a single anomalous frame smoothed by the largest window is one event.

**Tested behaviour** (`audit_b1_metric.py`; real pilot pass layout; synthetic traces; mean of 3 draws; P3 [P1]):

| Detector | A-G1 uncapped | A-G1 D = 25 | A-G1 D = 50 | A-G4 uncapped | A-G4 D = 25 | A-G4 D = 50 |
|---|---|---|---|---|---|---|
| Constant score | 0.663 [3.4] | **0.000 [42.0]** | 0.000 [22.0] | 0.566 [4.3] | **0.000 [42.3]** | 0.000 [22.3] |
| Slow drift (AR(1), phi = 0.999) | 0.410 | **0.129** | 0.186 | 0.351 | **0.108** | 0.158 |
| Random iid | 0.049 | 0.049 | 0.049 | 0.219 | 0.219 | 0.219 |
| Localized transient signal, V0 | 0.666 | 0.666 | 0.666 | 0.649 | 0.649 | 0.649 |
| Localized transient signal, MA(K) | 0.311 | 0.311 | 0.311 | 0.318 | 0.316 | 0.318 |
| Persistent real signal, V0 | 0.581 | 0.581 | 0.581 | 0.897 | 0.897 | 0.897 |
| Persistent real signal, MA(K) | 0.867 | 0.867 | 0.867 | 0.998 | 0.998 | 0.998 |

**Assessment.**

- The cap removes the persistence reward. The constant detector drops from P3 0.57 to 0.66 down to 0.
- It does not change detectors whose alarms are short: random, transient and persistent real signal are unchanged.
- It leaves a residual for slowly drifting scores (0.11 to 0.13). That is above random in A-G1 (0.05) and below random in A-G4 (0.22).
- D = 50 was tested as an alternative and is worse for drift, so D = 25 is frozen.
- **Interpretation.** The count is the number of alarm episodes, where one episode lasts at most 25 frames. It is approximately max(number of separate alarms, total alarm duration / 25). This is an interpretable burden: an operator receives a new alarm at least every 25 frames of continuous alarm.
- **New property introduced by the cap.** A single persistent source visible for v frames produces a run of up to v + K - 1 frames in a temporal variant at low thresholds. At A-G4 speed that is up to 41 frames, so 2 events, where V0 gives 1. At the half-amplitude threshold it counted once in every variant (median run 7 frames at A-G1 speed, 21 at A-G4 speed). This affects V0-vs-temporal comparisons (secondary) only, because V1, V2, V4 and every control share K.
- The residual drift effect is shared by all variants built from the same maps, and C0b's chance baseline preserves drift (section 19).

# 13. P1

**Threshold grid.** T = +infinity followed by every distinct value of {S_v(t) : t in N_f} union {q_p}, in descending order. Here:

- q_p = max over W_p of S_v;
- z_k = max over the passes of track k of q_p;
- R_pass(tau) = #{p : q_p >= tau} / n_passes;
- R_track(tau) = #{k : z_k >= tau} / n_tracks.

**P1.**

- tau\* = the first tau in T (the largest) with R_pass(tau) >= 0.80, evaluated as the integer test 5 x #detected >= 4 x n_passes.
- P1 = min(FA_env(tau\*), 50). The flag `censored` is set if FA_env(tau\*) > 50.

**Properties.**

- tau\* always exists, because R_pass = 1 at min(q_p), which is in T.
- The only unreachable case is the cap, which is flagged.
- Zero alarms give FA = 0.

# 14. P2

**P2.**

- tau_2 = the last tau in T (the smallest) with FA_env(tau) <= 2, evaluated as 1000 x Count <= 2 x \|N_f\|.
- P2 = R_track(tau_2).

**Properties.** tau_2 always exists, because FA_env(+infinity) = 0. FA_env is non-decreasing along T, so the qualifying set is a prefix of T.

# 15. P3

**Definition.**

- Points (x_j, y_j) = (FA_env(tau_j), R_pass(tau_j)), for the j with x_j <= 10.
- R(f) = max{ y_j : x_j <= f }, a right-continuous step function with **no interpolation**.
- P3 = (1/10) x integral from 0 to 10 of R(f) df.
- It is computed exactly: sort the distinct x values, take the maximum y at a duplicated x, and sum y_i (x_(i+1) - x_i) with x_last+1 = 10.

**Properties.**

- x_0 = 0 at tau = +infinity, so P3 is always defined and lies in [0, 1].
- Perfect separation gives P1 = 0, P2 = 1, P3 = 1.
- If the first finite threshold already has FA_env > 10, then P3 = 0.
- Chance level is not a closed form; it is estimated by section 19.

**Exact arithmetic.**

- FA values are 1000 x integer / \|N_f\|, and recalls are integer / n. So P1, P2 and P3 are rational numbers.
- Every decision quantity is computed as an **exact rational** (Python `fractions.Fraction` or integer arithmetic).
- **Rounding rule:** q9(x) = x rounded half-even to 9 decimal places (Python `decimal`, 60-digit context). The comparison with any threshold is made on q9(x).
- **For point estimates this rounding is lossless.** Every P3 is an integer multiple of 1 / (n_passes x \|N_f\|). A P3 difference and the threshold 1/50 are therefore either exactly equal or at least 1 / (50 x n_passes x \|N_f\|) apart. With n_passes <= 162 and \|N_f\| <= 43,744, that gap is at least 2.8 x 10^-9, larger than the 5 x 10^-10 rounding half-width. The same argument covers S, r and the C0a and P1 tests, because they are ratios of integer counts.
- Bootstrap bounds are floats. They are converted with their exact binary value, then passed through q9.

**Reference tests** (`test_ref_metrics.py`, all pass):

- ceil boundaries at L = 1, 25, 26, 50 and 51;
- a gap of 2 merges and a gap of 3 splits;
- an excluded frame splits a run;
- a merged span of 30 counts 2;
- a scenario boundary splits a run;
- the sweep equals the direct definition (1,500 random cases);
- a hand case with only the +infinity point at or below 10 FA gives P3 = 0 and P1 = 50 (censored);
- perfect separation gives (0, 1, 1);
- half separation gives P3 = 1/2;
- a one-alarm interior step gives P3 = 9/10.

# 16. False-alarm decomposition (C6): EXPLORATORY

**Status.** C6 is exploratory. **It has no role in C0 to C7, in any outcome, or in any confirmatory claim.** H2 is withdrawn as a hypothesis. The definitions below are frozen so that the exploratory analysis is not itself a forking path.

**Definitions (validation baselines per fold and seed):**

- b1(r, c) = mean of a_t(r, c) over validation frames;
- M3_t = 3 x 3 maximum, clipped at the borders;
- b3 = mean of M3_t over validation frames.

**Events and path quantities.**

- The events analysed are V0's FA runs at tau\*_V0. Each is classified at its first frame t_e, at p = (y\*, x\*) = argmax a_(t_e) (first row-major index on ties).
- **Peak excess:** E0 = a_(t_e)(p) - b1(p). **Floor:** E0_min = 0.1 x (tau\*_V0 - median(b1)).
- **Global-driven test:** s_(t_e) - (median(a_(t_e)) - median(b1)) < tau\*_V0. That is, the frame would not alarm without its global offset.
- **Fabric path:** x_j = x\* - U(t_e + j, j) for j = 1 .. J. J is the number of consecutive j <= K_(t_e) with 0 <= x_j <= 99 and known motion.
- rho = median_j [M3_(t_e+j)(y\*, x_j) - b3(y\*, x_j)] / E0.
- **Null path:** the same columns at rows y\* +/- 10 (only those inside 0..79). rho0 = median_j of the mean over those rows of [M3 - b3] / E0.
- **Camera path:** rho_cam = median_j [M3_(t_e+j)(y\*, x\*) - b3(y\*, x\*)] / E0.

**Classes, first match wins** (mutually exclusive and exhaustive by construction):

1. global-driven;
2. ambiguous-geometry (J < 3 or E0 < E0_min);
3. ambiguous-coincident (every \|x_j - x\*\| <= 1);
4. diffuse (rho0 >= 0.25);
5. camera-fixed (rho_cam >= 0.5 and rho_cam - rho0 >= 0.25 and rho_cam > rho);
6. persistent-local (rho >= 0.5 and rho - rho0 >= 0.25);
7. transient (rho < 0.25 and rho_cam < 0.25);
8. ambiguous.

**Synthetic check** (`audit_b7_c6.py`; counts over the synthetic cases that were events; A-G1 speed / A-G4 speed):

| Case | Result | Correct? |
|---|---|---|
| Transient | transient 40/40; 42/42 | Yes |
| Persistent fabric-fixed | persistent-local 48/49; 41/41 | Yes |
| **Camera-fixed** | camera-fixed 52/53; 44/44 | Yes (was 100% "transient" in v1.1) |
| **Global elevation** | global-driven 7/7; 10/12 | Mostly |
| **Vertical fabric-fixed line** | diffuse 39/39; 44/44 | Consistent label; it is *not* recognised as persistent |
| Exit-edge start, fast fabric | ambiguous 46/47 | Uninformative, not wrong |
| Persistent, late peak | too few first-frame events to judge | Blind spot |

**Why C6 is demoted, not promoted.**

- It depends on constants that were not validated on real data: +/-10 rows, 3 x 3, 0.25, 0.5, the 0.1 floor, and the threshold.
- It has no ground truth.
- In A-G1, about 37% of events are ambiguous from geometry alone.
- Removal rates (the v1.1 removal analysis, unchanged) and class shares are reported descriptively only, relative to seen-condition validation baselines.

# 17. Statistical analysis

**Per fold and seed, the following are reported:**

- P1, P2 and P3 for every variant;
- dP3 = P3(V4) - P3(V1);
- dP2;
- d1 = P1(V1) - P1(V4);
- G;
- for each control: the margin m_c = P3(V4) - P3(c) and the share S_c = m_c / G (only when q9(G) >= 0.02);
- log(P1(V4) / P1(V1)) (reported as "undefined" if either value is 0);
- paired bootstrap CIs (section 18) for dP3, dP2, the log P1 ratio and every m_c;
- McNemar: an exact two-sided binomial on discordant tracks at each variant's own tau_2 (V4 vs V1, V2, reverse, lagperm). Descriptive only.

**Status of the CIs.** CIs for control margins are reported, but the decision uses point margins (section 21). **No pilot quantity is reported as a confirmatory significance test** (section 27).

# 18. Bootstrap design

| Item | Frozen choice |
|---|---|
| Defect unit | Candidate track. A track carries all its passes. Every track has at least one pass by construction; scenarios without passes (T1_S177_I108_1) contribute only normal units |
| FA unit, scheme P (primary) | **Rotation-phase cluster.** Anchors are the first frames of maximal runs of consecutive frames with label in {2, 5}, in the same scenario. An anchor less than P_s / 2 frames after the previous accepted anchor is skipped. The phase is phi(t) = (t - last anchor at or before t) mod P_s; before the first anchor it is (t - first anchor) mod P_s; with no anchor at all it is (t - 1) mod P_s. 'mod' is the mathematical modulo, with results in [0, P_s). The skip test is the integer comparison 2 x (t - previous accepted anchor) < P_s. Cluster = (scenario, floor(phi / 50)). With the frozen periods that gives 18 clusters in A-G1 and 32 in A-G4 |
| FA unit, scheme B | Contiguous 1,200-frame blocks from frame 1 of each test scenario; the last partial block is kept. That gives 39 blocks in A-G1 and 22 in A-G4 |
| Stratification | None. Units are drawn from the fold's pool |
| Fold boundaries | Folds are bootstrapped separately and never mixed |
| Replicates | 2,000 per fold |
| RNG | `numpy.random.default_rng(20260924)`. Order: fold A-G1 then A-G4; within each replicate, tracks (n_tracks draws), then blocks (n_blocks), then phase clusters (n_clusters), all with replacement. **The same draws are used for every variant and every coreset seed** |
| Statistic per replicate | For each scheme, P1, P2 and P3 of every variant are recomputed. Recall uses the resampled passes with multiplicity. FA = 1000 x (sum of attributed event chunks over drawn units) / (sum of their N_f frames) at every tau in the original grid T. The envelope is rebuilt |
| CI | Percentile 2.5 and 97.5 of the replicate differences (numpy `percentile`, method 'linear'), per scheme |
| **Decision bound for C3** | LB_f = min(q9(lower bound under scheme P), q9(lower bound under scheme B)) |

**Why the unit is the rotation phase, not a longer block.** In TSFabrics the same fabric returns once per rotation for the whole recording (33 rotations in S555, 106 in S174_I111). A fabric-fixed false-alarm source therefore recurs at lags P, 2P, 3P and so on. A contiguous block of length L keeps only the pairs at lags below L inside a unit.

**Simulation** (`audit_b6_bootstrap.py`; real scenario lengths and periods; 3% of fabric locations are recurring sources): bootstrap SE divided by the true SD.

| Fold / sources | Blocks 600 | Blocks 1,200 | Blocks 2,400 | Phase clusters (true phase) |
|---|---|---|---|---|
| A-G1, none | 0.99 | 0.96 | 0.97 | 0.93 |
| A-G1, weak | 0.65 | 0.65 | 0.67 | 0.93 |
| A-G1, strong | 0.26 | 0.29 | 0.35 | 0.92 |
| A-G4, none | 0.99 | 0.95 | 0.90 | 0.99 |
| A-G4, weak | 0.88 | 0.87 | 0.87 | 1.05 |
| A-G4, strong | 0.38 | 0.41 | 0.38 | 0.96 |

**With estimated phase** (`audit_b6_phase_est.py`; 3% period drift per rotation; 10% of anchors missed; strong sources):

| Phase estimate | A-G1 | A-G4 |
|---|---|---|
| True phase | 0.82 | 1.01 |
| Fixed-period phase | 0.64 | 0.67 |
| **Cutline-anchored phase (frozen)** | **0.78** | **0.91** |

**Conclusions.**

- 1,200 is **not** justified as a fix. It captures at least 54% of the lag-P pairs, but almost none of the lag-kP pairs. Its SE ratio under recurring sources stays at 0.29 to 0.41. It is kept only as a second scheme, to cover non-periodic slow drift that phase clusters could split.
- The decision uses the more conservative of the two bounds.
- **Remaining dependence:**
  - between adjacent phase bins (within 25 frames of a bin edge);
  - from phase drift after missed anchors;
  - at the scenario level, which cannot be estimated with 3 to 5 scenarios.
- Even the frozen scheme gives about 0.78 x the true SE in A-G1 in simulation. **The C3 CI is still somewhat anti-conservative in A-G1.** This is declared in section 27.

# 19. Chance baseline

**Purpose.** It answers one question: is V0 better than a detector with the same score dynamics but no information about where defects are? It replaces v1.1's fixed P3 < 0.10 rule, which random scores exceed in A-G4 (chance P3 of about 0.18 to 0.22).

| Item | Frozen choice |
|---|---|
| What is shifted | V0's frame-score trace, separately within each test scenario, over the whole scenario including pass-window frames: shifted(t) = original(((t - 1 - d) mod N_s) + 1), which is `numpy.roll(x, d)` on the 0-based array |
| What stays fixed | Labels, passes, W_p, N_f, tracks, the threshold rule and the metric |
| Allowed offsets for scenario s | Integers d with ceil(N_s / 4) <= d <= floor(3 N_s / 4), d != 0, **and** ceil(P_s / 4) <= (d mod P_s) <= floor(3 P_s / 4). The phase restriction keeps every recurrence at least a quarter-rotation away from realignment |
| Number of shifts | 200 per fold and seed. Each shift draws one offset per scenario |
| RNG | `numpy.random.Generator(PCG64([20260925, fold_index, seed_index]))`; scenarios in lexicographic order; each offset is uniform over the allowed set via `integers(0, n_allowed)` |
| Chance statistic | P3 of each shifted trace, computed exactly as in section 15 |
| **Collapse rule** | k = #{shifts with P3_shift >= P3(V0)} (exact rational comparison). The fold is **collapsed iff k >= 10**, which is equivalent to p = (1 + k) / 201 > 0.05 |
| Folds | The same procedure in both folds. Each fold uses its own null. It is recomputed per coreset seed |

**Why it is appropriate.**

- The shift keeps V0's marginal distribution, its autocorrelation (except at one wrap point per scenario), its scenario-level offsets and its drift.
- It also keeps the exact window geometry, including grace-window chance credit.
- It destroys only the alignment between scores and defects.
- So the null P3 is what this metric gives a detector with V0's dynamics but no defect information. Nothing in it is tuned: the 0.05 level and the 200 shifts are fixed a priori.

**Tested** (`audit_b8_chance.py`; real layout; synthetic V0):

| Detector | A-G1: P3; p; collapsed? | A-G4: P3; p; collapsed? |
|---|---|---|
| Random V0 | 0.060; 0.557; **collapsed** | 0.171; 0.607; **collapsed** |
| Weak-signal V0 | 0.168; 0.005; not collapsed | 0.449; 0.005; not collapsed |
| Strong-signal V0 | 0.800; 0.005; not collapsed | 0.985; 0.005; not collapsed |

Without the phase restriction, the null maximum rose from 0.263 to 0.298 for random V0 in A-G4. The restriction costs nothing.

**Error rate.** By construction, a detector with no defect information escapes collapse with probability of about 5%.

# 20. C0 rules and validity precedence

Per fold and seed:

| Rule | Condition |
|---|---|
| C0a saturated | V0's R_pass at V0's own tau_2 >= 0.95 (integer test: 20 x #detected >= 19 x n_passes) |
| C0b collapsed | The section 19 rule |
| C0c motion-invalid | Section 7 item 8 |

**Validity state: one value, from one ordered chain** (independent of data-structure order):

1. if C0b, then `collapse`;
2. else if C0c, then `motion`;
3. else if C0a, then `saturated`;
4. else `valid`.

**Reason for this order.**

- Collapse concerns the detector itself and does not depend on motion.
- Motion invalidity prevents V4 from being computed properly.
- Saturation only removes headroom.

**There is no separate "statistically invalid" state.** Every statistic in sections 13 to 19 is always defined. Any NaN, infinity or exception in Stage 3 aborts the run. That is an execution failure, not a validity state (section 24).

# 21. C1, C2, C3, C4 and C7 rules

Every comparison is made on q9 values (section 15). The bands for dP3 are:

- **harm:** q9(dP3) <= -0.02;
- **null:** -0.02 < q9(dP3) < 0.02;
- **positive:** q9(dP3) >= 0.02.

**Boundary behaviour:**

| Value | Band |
|---|---|
| exactly -0.02 | harm |
| 0 | null |
| exactly +0.02 | positive |
| 0.30 - 0.28 in float64 (0.019999999999999962) | positive, because q9 = 0.020000000 |
| exact rationals such as 3/10 - 7/25 | positive |

**Floating-point boundary tests (AT-16).** These values would be misclassified by raw float comparison and are correct after q9:

| Expression (float64) | Raw value | q9 | Compared with | Result |
|---|---|---|---|---|
| 0.30 - 0.28 | 0.019999999999999962 | 0.020000000 | dP3 band | positive |
| -(0.30 - 0.28) | -0.019999999999999962 | -0.020000000 | dP3 band | harm |
| 0.3 - 0.1 | 0.19999999999999998 | 0.200000000 | S <= 0.2 | fail |
| 0.7 - 0.2 | 0.49999999999999994 | 0.500000000 | S >= 0.5 | pass (if the margin also passes) |
| 0.7 + 0.1 | 0.7999999999999999 | 0.800000000 | r <= 0.80 | pass |
| 0.1 + 0.2 - 0.3 | 5.55e-17 | 0.000000000 | LB_f > 0 | **not** > 0 |
| 1.1 - 1.04 | 0.06000000000000005 | 0.060000000 | dP2 >= 0.06 | pass |

| ID | Definition |
|---|---|
| C1 (per fold) | Both P1 values 0: `nonevaluable`. P1(V1) = 0 < P1(V4): `fail`. Both censored: `nonevaluable`. Otherwise r = P1(V4) / P1(V1), with censored values = 50: `pass` if q9(r) <= 0.80, `fail` if q9(r) > 0.95, else `between`. Only `pass` is ever used; under one-sided censoring the `fail` and `between` labels are not interpretable. **C1 overall = pass in both folds** |
| C2 | q9(dP2) >= 0.06 in both folds |
| **C3** | Band = positive in **both** folds, **and** LB_f > 0 in at least one fold |
| **C4** (per fold, only in a positive fold) | For each control c in {V2, REV, LAG}: **fail** if q9(S_c) <= 0.2; **pass** if q9(S_c) >= 0.5 **and** q9(m_c) >= 0.02; else **between**. Fold C4 = fail if any control fails; pass if all three pass; else between. **C4 overall = pass in both folds** |
| C5 | Diagnostic: L_f = (P3(oracle) - P3(V4)) / G |
| C7 | For each of dP3, dP2 and d1 (d1 is skipped if C1 is nonevaluable in either fold): **fail** if the q9 signs in the two folds are strictly opposite. Zero is neutral |

**How C4 handles the edge cases.**

- A control that beats V4 has m_c < 0, so S_c < 0: fail.
- A control worse than V1 has S_c > 1; it passes if m_c >= 0.02.
- S_c is never undefined, because it is computed only when q9(G) >= 0.02.
- Every control's P3 is always defined (>= 0). A control is never "invalid"; its fallback frames equal V2 by definition.
- **V4 cannot pass C4 by beating V1 while V2 performs equally well or better.** That case gives S_V2 <= 0 (fail, so E) or m_V2 < 0.02 (so not pass).

# 22. Decision state machine

Evaluated per coreset seed. The first matching step decides.

| Step | Condition | Outcome |
|---|---|---|
| 1 | Both folds invalid | **G** if either is `collapse`; else **M** if either is `motion`; else **F** |
| 2 | Exactly one fold invalid | **B\*** (inconclusive) |
| 3 | Band = harm in either fold | **D** (alignment harmful) |
| 4 | Band = null in both folds | **C** (null) |
| 5 | A positive fold has C4 = fail | **E** (the gain is explained by a control) |
| 6 | C3 and C4 overall and C7 and (C1 or C2) | **A** (supported) |
| 7 | Otherwise | **B** (inconclusive) |

**Seed follow-up.**

- Coreset seeds 1 and 2 are computed in the same Stage 3 pass as seed 0 (section 24), so no human decision is needed.
- If the seed-0 outcome is C, D, E, F, G or M, **it is final**. The seed 1 and 2 outcomes are reported descriptively and cannot change it.
- If the seed-0 outcome is A, B or B\*:
  - B and B\* on any seed are mapped to **I** (inconclusive, stop);
  - the final outcome is the most severe across seeds 0 to 2, in the order G > M > F > D > E > C > I > A.
- **A is final only if all three seeds give A.**

| Final | Meaning | Consequence |
|---|---|---|
| A | Correspondence-specific improvement supported in both folds, robust to coreset seed | Proceed to Stage 2 (a new pre-registration) |
| C | Null | Stop the alignment question; report as a null result |
| D | Harmful | Stop; report as a negative result |
| E | The gain exists but a control explains it | Stop; report that correspondence is not supported |
| I | Inconclusive | Stop; report as inconclusive. No re-running |
| F, M | Invalid test | Report as invalid on these folds |
| G | Detector collapse | Pivot to the condition-shift adaptation question |

**Exhaustive enumeration** (`audit_decision_enum.py`).

Per-fold primitive grid:

- validity flags, 2^3;
- dP3 in {-0.03, -0.02, -0.02 + 1e-9, -0.01, 0, 0.01, 0.02 - 1e-9, 0.02, 0.03, 0.04, 0.2};
- each of the three control shares in {-1, 0.2, 0.2 + 1e-9, 0.5 - 1e-9, 0.5, 1}, with margins derived as S x G;
- CI lower bound in {-0.01, 0, 0.001};
- 8 P1 pairs covering zero, ratio boundaries and censoring;
- dP2 in {-0.06, 0, 0.06 - 1e-9, 0.06}.

Coverage:

- 1,824,768 primitive states per fold; **3,329,778,253,824 two-fold states**.
- These are evaluated through 1,120 distinct per-fold signatures. The compression was verified on 300,000 random primitive pairs: 0 mismatches.

Outcome counts over this grid (these are not probabilities):

| Outcome | Count |
|---|---:|
| A | 251,100 |
| B | 5,699,808,036 |
| B\* | 728,388,993,024 |
| C | 10,749,542,400 |
| D | 17,199,267,840 |
| E | 18,378,915,840 |
| F | 52,027,785,216 |
| G | 2,081,111,408,640 |
| M | 416,222,281,728 |

**Checks, all passed (0 violations):**

- A separately written closed-form partition, with one predicate per outcome and no ordering, has **exactly one true predicate in every state**, and it equals the chain's outcome.
- A never occurs with a fold below +0.02, a control margin below 0.02, a control share below 0.5, or an invalid fold.
- An invalid fold is never overridden.
- In the follow-up over all 729 seed triples, no seed-0 B or B\* ends as A, and A requires A on all three seeds.
- Validity precedence does not depend on dictionary key order.

# 23. Acceptance tests

"rel" means max\|a - b\| / max\|b\| over all elements (infinity-norm ratio). Every test runs before any test-scenario detector output exists.

Stage key:

- S1 = Stage 1: synthetic or reference only; CPU.
- S2 = Stage 2: bank and validation frames; GPU where noted.
- S3-pre = the start of Stage 3, before any test frame is scored.

**Failure consequence for AT-01 to AT-16:** Stage 3 may not start. Fix the code and rerun the stage. If the specification itself is wrong, issue v1.2.x before Stage 3.

| ID | Fixture | Expected property | Tolerance | Pass rule | CPU | Stage |
|---|---|---|---|---|---|---|
| AT-01 | 1 validation frame | Shapes: layer2 (1, 512, 80, 100); layer3 (1, 1024, 40, 50); features (8000, 1024); map (80, 100) | exact | all equal | GPU | S2 |
| AT-02 | 5 validation frames | D4 order equals the official order (interpolate the unfolded features, then MeanMapper) | rel <= 1e-5 | all frames | GPU | S2 |
| AT-03 | 2,000 validation queries vs seed-0 coreset | fp32 minimum squared distance equals the float64 brute-force minimum | max_q \|d32 - d64\| / max_q d64 <= 1e-4 | criterion met. Argmin agreement is reported but **not gated** | GPU | S2 |
| AT-04a | 10 validation frames, same process, same batch composition | Maps reproduce | exact | bit-identical | GPU | S2 |
| AT-04b | The same 10 frames with batch size 1 vs 4 | Batch independence | rel <= 1e-6 | criterion met | GPU | S2 |
| AT-04c | All validation frames recomputed at the start of Stage 3 (possibly on another GPU) | Stage 2 constants reproduce | rel <= 1e-4 on maps; relative difference <= 1e-4 on mu0 and tau_cell | criterion met; the Stage 2 constants are used. **If it fails, Stage 2 is repeated on the Stage 3 hardware before any test frame is scored** (no test information exists yet) | GPU | S3-pre |
| AT-05 | Seeded smooth random texture (640 x 2,000); crops shifted by -10 px and +7 px | Phase-correlation sign and magnitude; inputs not mutated | dx within 0.1 of truth; \|dy\| <= 0.1 | both shifts; inputs byte-equal after the call | Yes | S1 |
| AT-06a | Constant background b; a single-cell impulse of amplitude A fixed to the fabric at row 40, column 95 in frame 0, moving left 5 cells/frame (dx = -40 px); evaluated at frame 11 with K = 8, where the impulse is at column 40 and every read of V4 and V4-reverse is valid | V4 at (40, 40) = A exactly (all K terms aligned); V4-reverse at (40, 40) = (A + (K - 1) b) / K; V2 at (40, 40) = (A + (K - 1) b) / K | 1e-12 (float64) | exact to tolerance | Yes | S1 |
| AT-06b | 200 consecutive reliable validation pairs (T1_S164_I199_1), images averaged 8 x 8 to 80 x 100 | Warp direction on real frames: MSE(img_t, W(img_(t-1), U(t,1))) < MSE with -U(t,1) on valid cells | none | holds for >= 95% of pairs | Yes | S2 |
| AT-07 | Seeded random maps (float64) | V4 with U forced to 0 == V2; V1 == V0 when K = 1; V2 == V0 for identical maps; lagperm == V4 when K <= 2; V4-reverse(a) == V4(mirror(a)) | 1e-12 | all identities | Yes | S1 |
| AT-08 | K = 1..25 plus synthetic motion | pi is a bijection with pi(0) = 0 and no fixed point for K >= 3; validity masks, prior-fill counts and source columns equal V4's; source-frame multiset equals V4's; \|Delta_i\| >= floor(\|dx\| / 8) | exact | all | Yes | S1 |
| AT-09 | Synthetic maps and motion; frames after t are replaced by different random maps and motion | V0, V1, V2, V4, V4-reverse and V4-lagperm at t are unchanged; K_t = min(k_t, t) at t = 1, 2, 3; motion-unknown fallback returns V2 exactly | exact | all | Yes | S1 |
| AT-10 | Synthetic maps with known U giving known invalid columns | Number of mu0-filled cells = 80 x sum_i #invalid columns(U_i); filled value = mu0; C-REV masks are mirrored | exact | all | Yes | S1 |
| AT-11 | 1,000 random timelines plus the section 15 hand cases | The implementation's event counts, FA_env, P1, P2, P3, C1 to C7 and outcomes equal the reference scripts. The implementation must itself use exact rational or integer arithmetic for point estimates | exact rational equality | 0 mismatches | Yes | S1 |
| AT-12 | The section 22 grid | Implementation outcome counts equal the reference counts; 0 invariant violations | exact | equal | Yes | S1 |
| AT-13 | Real pilot pass layout (frozen CSV), constant score | P3 = 0 in both folds; D = 25 rule active | exact | equal | Yes | S1 |
| AT-14 | Frozen label files and bank CSV | Per-scenario label counts equal the forensic table; capacities and v1.2 quotas reproduce section 4 | exact | equal | Yes | S1 |
| AT-15 | Section 19 generator | Offsets reproduce from the seed; all lie in the allowed set; none is 0; on the synthetic real-layout cases, random V0 collapses and strong V0 does not | exact | all | Yes | S1 |
| AT-16 | The boundary values of section 21 (float and rational) | Band assignment as tabulated | exact | all | Yes | S1 |
| AT-17 | The section 16 synthetic cases | C6 classes as tabulated | the section 16 counts +/- 10% | if it fails, **C6 is not reported**; **Stage 3 is not blocked** | Yes | S1 |

# 24. Three-stage blinded execution protocol

**Stage 1: structural and unit validation.**

- **Allowed:** synthetic maps and motion, reference scripts, unit and acceptance tests AT-05 to AT-17, the frozen CSVs (labels, passes, tracks, bank), and label-count checks.
- **Forbidden:** any image-derived detector output on any scenario; any TSFabrics test score, table, P1/P2/P3 or decision.
- **Output:** `stage1_report.json` with the pass/fail result of every test, plus hashes.

**Stage 2: pipeline and development validation.**

- **Data allowed:**
  - bank frames of both folds;
  - validation frames (T1_S164_I199_1, frames 1 to 1,212);
  - motion estimation on all training-side scenarios of each fold (for tau_r).
- **Computed:**
  - bank features;
  - coresets for seeds 0, 1 and 2 per fold;
  - validation maps per seed;
  - mu0, b1, b3, tau_cell;
  - deployment thresholds;
  - tau_r;
  - AT-01 to AT-04b and AT-06b;
  - the b1 left-right profile.
- **May be inspected:** validation maps and scores, runtimes, memory, motion statistics of training-side scenarios.
- **Forbidden:** computing anomaly maps, scores or metrics on any frame of any test scenario of either fold. The only features ever computed on such frames are **bank features** (A-G1's bank draws from G4 scenarios; A-G4's bank draws from G1 scenarios). Those features go into the coreset only and are never scored, displayed or summarised.
- **Frozen at the end of Stage 2** (`frozen/`):
  - the configuration file;
  - coreset indices and vectors;
  - validation constants per seed;
  - tau_r per fold;
  - the environment record;
  - the git commit.
- **Any code change after this point** is a deviation, logged with date and reason.

**Stage 3: locked test evaluation.**

- **Preconditions, checked by the runner, which refuses to start otherwise:**
  - the git working tree is clean and the commit is recorded;
  - the configuration hash equals the frozen one;
  - the environment is recorded;
  - `stage1_report.json` and the Stage 2 test results are all PASS;
  - the frozen-file hashes verify.
- **One command** (`scripts/run_stage3.py --config configs/pilot_v1_2.yaml`) performs, in order:
  1. AT-04c;
  2. test-frame features and maps against all three seed coresets in a single pass;
  3. motion on test scenarios;
  4. all variants;
  5. windows, N_f, events, P1/P2/P3;
  6. the chance baselines;
  7. the bootstrap;
  8. the criteria;
  9. the decision and follow-up;
  10. the report.
- **Logs:** until step 10, the log prints only progress counts (frames processed per scenario). It prints no score, rate or metric.
- **Resumption:** after a platform interruption, the runner resumes from the per-scenario outputs already written and hashed, with the same code and configuration. That is not an intervention.
- **Prohibited after test outputs exist:** manual threshold changes, formula changes, re-running under alternative settings (other than the section 26 sensitivity analyses, which the same run produces), and discarding or replacing the run of record.
- **If a bug is found after the report exists,** the run of record stays the primary result. A corrected run is reported alongside it, labelled "post-hoc corrected", and the pilot is labelled "deviated".

# 25. Reproducibility, hashing and repository structure

**Repository** (small modules; the reference code is kept separate from the pipeline):

```text
tsfabrics-alignment-pilot/
  README.md                    how to run the three stages
  PREREGISTRATION.md           this document (its SHA-256 is recorded in the run manifest)
  requirements.txt             pinned versions (torch, torchvision, opencv-python, numpy, pyyaml)
  configs/pilot_v1_2.yaml      every constant in this document
  data/frozen/                 labels index, passes/tracks CSV, bank CSV v1.2, periods CSV (with sha256sums.txt)
  third_party/patchcore/       pinned at fcaa92f (git submodule)
  src/tsfpilot/
    frames.py                  frame listing, decoding, label loading
    bank.py                    section 4 rule
    detector.py                PatchCore-derived features, coreset wrapper, distances, maps
    motion.py                  section 7
    windows.py                 k_t, K_t, U(t, i)
    variants.py                section 9
    passes.py                  W_p, N_f, carry-over flags
    events.py                  section 12
    metrics.py                 sections 13 to 15 (exact arithmetic)
    chance.py                  section 19
    bootstrap.py               section 18
    decision.py                sections 20 to 22
    decomposition.py           section 16 (exploratory)
    manifest.py                hashing and run records
  reference/                   frozen copies of the v1.2 reference scripts (never imported by src/)
  tests/                       pytest: test_reference.py, test_acceptance_stage1.py, fixtures/
  scripts/                     run_stage1.py, run_stage2.py, run_stage3.py
  runs/<run_id>/               outputs of one run (never edited)
```

**Stage 3 outputs, per fold, in `runs/<run_id>/`:**

| File | Content |
|---|---|
| `scores_<fold>_seed<s>.npz` | Per-frame scores of V0 to V4-oracle, statuses, dx, K_t |
| `maps_<fold>_seed0/<scenario>.npy` | float32 maps, seed 0 only (for C6) |
| `units_<fold>.json` | Windows, N_f, tracks, clusters, blocks, carry-over flags |
| `metrics_<fold>_seed<s>.json` | Exact rationals as strings and q9 decimals |
| `chance_<fold>_seed<s>.json` | Offsets and null P3 values |
| `bootstrap_<fold>.npz` | Replicate statistics |
| `criteria_seed<s>.json` | |
| `decision.json` | |
| `sensitivity.json` | |
| `report.md` | |
| `env.txt` | `pip freeze`, `nvidia-smi`, Python, CUDA, cuDNN |
| `manifest.json` | For every file: path, bytes, SHA-256; plus the git commit, the config hash, the PREREGISTRATION.md hash, the hashes of the frozen Stage 2 files, the Kaggle dataset version, and the SHA-256 of the sorted list of (image path, byte size) for every frame used. The manifest's own SHA-256 is printed as the last line and recorded in the project log |

# 26. Sensitivity analyses

All of these are pre-specified and produced by the same Stage 3 run. **None of them can change an outcome.**

| ID | Analysis |
|---|---|
| S1 | No-grace recall (W_p = [s_p, e_p]) |
| S2 | Carry-over-affected passes removed (section 11) |
| S3 | **Track-balanced P3:** each pass weighted 1 / (n_passes of its track x n_tracks). In A-G1 the largest track holds 51 of 162 passes (31%) and the top three hold 57%; in A-G4 the figures are 24 of 99 and 41% |
| S4 | Leave-largest-track-out dP3, per fold (largest by pass count; ties broken by lexicographic track id) |
| S5 | Uncapped event counting (the v1.1 definition), descriptive |
| S6 | CIs under each bootstrap scheme separately, plus 600-frame blocks |
| S7 | Fixed k in {5, 10, 20}; scaled k with c in {0.5, 2}; shift-scale dose response c in {0.5, 1.5} |
| S8 | Label-4-only P2 and P3 |
| S9 | Deployment table (validation threshold at FA_env <= 2) |
| S10 | Frame AUROC and AUPRC; pixel AUPRO (map variants; label 5 excluded) |
| S11 | V4-oracle and C5 |
| S12 | Exploratory C6 and the mechanism index B |
| S13 | Seed 1 and 2 outcomes whenever seed 0 is final |

# 27. Limitations

1. **Track concentration.** Pass-level recall is dominated by a few tracks: the top three hold 57% of passes in A-G1 and 41% in A-G4. dP3 >= 0.02 in a fold can be produced by one physical defect. S3 and S4 must be reported next to any A outcome.
2. **Bootstrap coverage.** Even the frozen phase-cluster scheme recovers about 0.78 of the true SE in A-G1 in simulation (18 clusters). The C3 CI is mildly anti-conservative there. The pilot's CIs are **not** presented as confirmatory inference.
3. **Point-estimate controls.** The C4 margins are point estimates with a practical 0.02 band. Their CIs are reported but not gated. The 0.02 band is a practical-significance threshold fixed before any score, not a noise-calibrated one.
4. **Residual drift credit** in P3 (0.11 to 0.13 for a slowly drifting score). It is shared by all variants built from the same maps and is covered by the chance baseline for C0b.
5. **Cap interaction.** At low thresholds a temporal variant can count one persistent source twice in A-G4. This affects comparisons between V0 and the temporal variants only.
6. **C-REV** is confounded with left-right map asymmetry, because every test scenario moves left. **C-LAG** weakens at low speed and for wide defects. That biases against A but **toward E**. An E outcome triggered only by C-LAG in A-G4 must be reported together with the per-frame misalignment distribution, because it may reflect a weak control rather than an absent correspondence effect.
7. **Validation baselines** (mu0, b1, b3, tau_cell) come from a seen-condition group. They are shared by both folds (one scenario) and give a coarse deployment table.
8. **Label semantics.** Label 5 is cutline-linked. The 10 passes labelled [4, 5] mix a defect and a cutline. S8 reports label-4-only results.
9. **Blinding is procedural.** A single researcher runs Kaggle. Hashes, the single-command runner and silent logs make a breach detectable and deliberate, not impossible.
10. **Two folds, 3 to 5 scenarios each.** There is no scenario-level inference. An A outcome licenses only a new, separately pre-registered Stage 2.

# 28. Literature-positioning caveats

These are unchanged from v1.1 A16:

- No novelty is claimed for motion alignment or shift-and-add.
- ST-PaveCLIP is described as homography-warped recursive fusion of **supervised** anomaly maps, which gave fewer false positives with a longer duration tail.
- Lu et al. 2022 is cited as normal-only lace video anomaly detection, noting that its full text was not examined.
- "No prior work does X" is stated only as "to our knowledge, in the searches reported".
- Every literature number is re-checked against the PDFs before any manuscript.
- The PatchCore paper's image-score equation must be checked before it is contrasted with the code.

# 29. Researcher degrees of freedom audit

A = scientifically irrelevant; B = frozen in this document; C = implementation detail, documented in the run record.

**Frozen (B):**

| Choice | Class | Where frozen |
|---|---|---|
| Event cap D, merge gap, span length, chunk attribution | B | Section 12 |
| Threshold grid, equality (>=), integer comparisons, envelope | B | Sections 13 to 15 |
| Rounding before every comparison (q9, half-even) | B | Section 15 |
| Null band and boundary behaviour | B | Section 21 |
| Control set, pass/fail/between rules | B | Section 21 |
| Validity precedence | B | Section 20 |
| Chance-shift generation, count, seed, collapse rule | B | Section 19 |
| Bootstrap units, anchors, bin width, block length, replicates, RNG order, CI method, decision bound | B | Section 18 |
| Validation scenario, bank quotas | B | Section 4 |
| Per-seed validation constants | B | Section 8 |
| k_t at m_t = 0; the g_p range; float64 accumulation | B | Sections 8 and 11 |
| Coreset input order, device, chunk size; coresets built once and saved | B | Section 6 |
| Frame index (1-based, from the file name as in the forensic inventory; 0 missing indices) | B | Section 23, AT-14 |
| NaN or infinity anywhere | B (abort) | Section 20 |
| Carry-over rule | B | Section 11 |
| numpy median and percentile conventions | B | Sections 8 and 18 |

**Documented (C) and irrelevant (A):**

| Choice | Class | Where handled |
|---|---|---|
| Library versions, GPU type | C | `env.txt`; AT-04c |
| Last partial batch | C | Covered by AT-04b |
| Order of scenarios within a fold | A | Any |
| Storage format | A | Section 25 |

**Constants set with knowledge of whole-dataset descriptive statistics** (no detector output and no defect-level result was used; the pass layout was used to test the metric rules):

- the choice of pilot folds: one fast group and one slow group. **The pilot-fold selection was informed by whole-dataset statistics**;
- the k bounds 3 and 25, and therefore the cap D = 25;
- the rotation periods P_s (from cutline labels, including test scenarios), used by the chance-shift restriction and the phase clusters;
- the phase bin width of 50 frames and the 1,200-frame block length;
- the A-G4 validation reallocation, from the forensic scenario table;
- the null band 0.02, and the C0, C1 and C4 thresholds (set in v1.0 before any score existed);
- the tests of the B1 cap, the chance baseline and the bootstrap, which were run on the **real pilot pass layout** (test labels, no scores). They selected rules for their behaviour on uninformative and informative synthetic detectors, not for any outcome.

# 30. Pre-implementation checklist

- [ ] This document is approved and its SHA-256 recorded in the project.
- [ ] The repository is scaffolded per section 25, with the reference scripts copied unchanged into `reference/`.
- [ ] `third_party/patchcore` is pinned at `fcaa92f`.
- [ ] `configs/pilot_v1_2.yaml` contains every constant in sections 4 to 22.
- [ ] Stage 1 passes AT-05 to AT-17 (AT-17 may fail without blocking).
- [ ] Stage 2 passes AT-01 to AT-04b and AT-06b; constants, coresets and the environment are frozen and hashed.
- [ ] The Stage 3 runner's precondition checks and silent logging are verified on a dry run over **validation frames only**.
- [ ] Stage 3 is run once. The manifest hash is recorded.

# 31. Fresh adversarial audit of v1.2

I re-read sections 2 to 30 as a hostile reviewer, not as their author. Each finding is either **resolved in the text**, meaning the text fully fixes it, or a **residual**, meaning it is disclosed and non-blocking, with the reason.

**A. Metric gaming.** *Can temporal averaging improve the metric by creating longer alarms?*

- **No beyond 25 frames.** A run of L frames costs ceil(L / 25). The constant detector scores P3 = 0 (AT-13).
- **Residual 1:** within 25 frames, smoothing can merge several nearby V0 alarms into one episode. That is the ordinary operator-facing benefit of temporal smoothing. V1, V2, V4 and all controls share it at equal K, so it cannot create a V4-specific gain.
- **Residual 2:** slow drift keeps P3 of about 0.11 to 0.13. It is shared by all variants built from the same maps.
- Non-blocking.

**B. Control gaming.** *Can V4 pass while V2 or lagperm explains the result?*

- **No.** A requires m_c >= 0.02 and S_c >= 0.5 against V2, reverse and lagperm in both folds.
- A control explaining at least 80% of the gain gives E.
- Could V4 beat all three for a non-correspondence reason? C-LAG shares every quantity except the pairing, and C-V2 shares everything except warp and fill. A non-correspondence reason would have to distinguish V4 from C-LAG, which differs only in pairing. That is the definition of a correspondence effect.
- **Residual:** C-LAG's misalignment is weak at low speed and for wide defects. That biases **against** A.
- Non-blocking.

**C. Statistical gaming.** *Can CIs become artificially narrow?*

- **Yes, somewhat, in A-G1.** About 0.78 x the true SE in simulation, and a few tracks dominate the passes.
- The CI enters only C3, and only as "lower bound > 0 in at least one fold", using the more conservative of two schemes.
- No pilot CI is presented as confirmatory.
- Track concentration is reported through S3 and S4.
- Non-blocking. A stricter CI rule would change the pre-registered power, not remove an ambiguity.

**D. Leakage.** *Can test information influence a threshold, the bank, a control, the chance baseline or a decision?*

- Checked item by item. **No test score or map reaches any of them:**
  - fold assignment, clusters, groups: frozen CSVs;
  - bank: training side;
  - validation: a scenario that is a test scenario nowhere;
  - tau_r: training-side motion;
  - k: causal and label-free;
  - thresholds: fixed rules per variant;
  - bootstrap units: labels, no scores;
  - chance baseline: shifts V0 only;
  - sensitivity analyses: produced by the locked run;
  - staging: section 24.
- **Residual:** some rules were chosen by testing them on the real test pass layout (labels only). This is disclosed in section 29. Their behaviour was judged on synthetic detectors, not on outcomes.
- Non-blocking.

**E. Boundary ambiguity.** *Can floating-point representation change an outcome?*

- **No for point estimates.** They are exact rationals, rounded losslessly to 9 dp.
- Bootstrap bounds are floats rounded to 9 dp. A flip would need a lower bound within 5 x 10^-10 of 0 on one machine and not the other. That is recorded, not decisive in practice.
- Boundary tests: AT-16.
- Resolved.

**F. Implementation freedom.** *Could two competent researchers get different outcomes?*

- Every decision-relevant choice is listed as frozen in section 29, and AT-11 and AT-12 bind the implementation to the reference.
- The remaining freedom is at the numerical level: library and GPU. It is bounded by AT-04, and the coresets are built once and reused.
- A different platform could build a different coreset in Stage 2. That behaves exactly like a different seed, and the follow-up rule requires all three seeds to agree for A.
- Resolved.

**G. Staging.** *Can test results be seen before code and configuration are frozen?*

- Not without a detectable, deliberate breach: preconditions, silent logs, a single command and a manifest.
- **Residual:** the blinding is procedural, because one person controls the Kaggle notebook and could open the score arrays. Disclosed.
- Non-blocking.

**H. Chance baseline.** *Can a collapsed detector pass C0b?*

- **Yes, with probability of about 5%, by design** (alpha = 0.05; 200 shifts).
- A detector whose only "information" is scenario-level offsets, drift or grace-window noise does not gain from them, because the null keeps all three.
- Periodic realignment of recurring defects is excluded by the phase restriction.
- Resolved as designed.

**I. False-alarm decomposition.** *Can C6 produce misleading categories?*

- **Yes:**
  - vertical fabric structures are labelled "diffuse", not persistent;
  - late-peaking events are blind spots;
  - exit-edge events are ambiguous at high speed.
- That is why C6 is exploratory, with no decision or confirmatory role.
- Resolved by demotion.

**J. Decision machine.** *Can any state produce zero or multiple outcomes?*

- **No.** It is an ordered chain with an unconditional else.
- An independent closed-form partition has exactly one true predicate in every one of 3.33 x 10^12 grid states.
- There are 0 invariant violations, and the follow-up cannot turn inconclusive into A.
- Resolved.

**K. PatchCore fidelity.** *Could the implementation differ materially from the intended detector?*

- The intended detector **is** the PatchCore-derived one with D1 to D7, not canonical PatchCore. The wording says so throughout.
- AT-02 and AT-03 bind the feature path and distances.
- **Residual:** D1 (full resolution) changes the effective receptive-field scale relative to the published configuration. That is a declared design choice, identical for all variants.
- Resolved.

**L. Remaining researcher degrees of freedom that could materially influence the result.**

- **None unfrozen.** The list in section 29 is exhaustive to my knowledge.
- The choices that *did* influence the design are the disclosed whole-dataset constants. They are fixed before any score exists and apply identically to V4 and to every comparator and control.

**Specification defects the fresh audit found in my first draft of v1.2, corrected in this text before freezing.** None changes the science. Each would otherwise have been a choice left to the programmer.

| # | Defect in the draft | Why it mattered | Correction now in the text |
|---|---|---|---|
| 1 | Stage 2 forbade computing "features on any frame of a test scenario of either fold", yet each fold's bank draws frames from the other fold's test scenarios | A self-contradiction: the protocol could not be followed as written, and a programmer would have had to pick an interpretation | Section 24: bank features are the only features computed on such frames; they are never scored, displayed or summarised |
| 2 | The same symbol L_f was used for the C3 bootstrap bound and the C5 oracle ratio | Ambiguous criterion | C3 bound renamed LB_f |
| 3 | The lossless-rounding argument was stated incorrectly | The claim "rounding cannot decide an outcome" was not proven as written | Section 15: the corrected bound, a gap of at least 2.8 x 10^-9 versus a 5 x 10^-10 half-width |
| 4 | There was no path when AT-04c fails (Stage 3 on a different GPU from Stage 2) | The implementer would be stuck, or tempted to loosen the tolerance | AT-04c: repeat Stage 2 on the Stage 3 hardware first |
| 5 | The AT-06a fixture did not fix the positions, so the expected V4-reverse value depended on mu0 fills | The test was not deterministic | Positions fixed so every read is valid; exact expected values given |
| 6 | The circular-shift direction and the modulo convention for negative phase were unstated | Two implementations would draw different nulls from the same seed | Section 19 formula (numpy.roll); section 18 mathematical modulo and an integer skip test |
| 7 | "float64 accumulation" named maps only, not V1's score sums | V1 could be accumulated in float32 | Section 8: all temporal sums |
| 8 | C0a did not say whose tau_2 is used | Ambiguous | V0's own tau_2 |
| 9 | S4 had no tie rule for the "largest track" | Non-deterministic sensitivity analysis | Tie broken by track id |
| 10 | The manifest did not identify the dataset version | Reproducibility gap | Dataset version plus a hash of the frame listing |
| 11 | There were no explicit float boundary tests for 0.2, 0.5, 0.8 and 0 | Requested in B9 | Section 21 table and AT-16 |

**Interactions created by the new fixes (checked):**

| Interaction | Assessment |
|---|---|
| Cap x chance baseline | Both use the same metric, so they are consistent |
| Cap x bootstrap | Chunk attribution keeps additivity |
| V2 control x motion fallback | Fallback frames make V4 = V2, which shrinks m_V2. Conservative |
| New validation x tau_r | Unchanged set |
| New validation x bank | A-G4 quotas re-derived by the frozen rule |
| Phase clusters x label 5 inside passes | Anchors only define phase; they are never evaluation frames |
| Per-seed constants x one-pass Stage 3 | Stage 2 builds all three seeds' constants |
| Stricter C3/C4 x power | A is harder to reach. This is the intended trade-off, not an ambiguity |

# 32. Final verdict

**READY FOR CODING**

No scientifically material ambiguity, leakage pathway, metric pathology, control weakness, or implementation freedom remains that would prevent coding under the frozen v1.2 specification.

The ten residuals in section 27 are real and must travel with any result. They are properties of a two-fold pilot on this dataset, disclosed and bounded. They are not open choices. The two that most limit how an A outcome may be read are track concentration and the A-G1 bootstrap coverage.

# Appendix: change log v1.1 to v1.2

| ID | Change | Blocker addressed | Effect |
|---|---|---|---|
| CL-01 | Event runs count ceil(L / 25); span length; chunk attribution | B1 | A constant detector no longer earns P3 |
| CL-02 | A-G4 validation moved to T1_S164_I199_1; A-G4 bank G2 = I192 50, I193 50 | B5 (overlap) | No validation scenario is a test scenario in either fold |
| CL-03 | C3 requires dP3 >= 0.02 in both folds | B2 | No one-fold null counts as positive |
| CL-04 | C4 controls {V2, REV, LAG}; margin >= 0.02 plus S >= 0.5 | B2, B3 | V4 must beat unaligned map averaging and both wrong-correspondence controls |
| CL-05 | Acceptance tests AT-01 to AT-17 with fixtures and tolerances | B4 | The implementation is bound to the specification |
| CL-06 | Three-stage protocol, single-command Stage 3, silent logs, manifest | B5 | Results cannot be seen before the freeze without a detectable breach |
| CL-07 | Bootstrap FA units: cutline-anchored phase clusters plus 1,200-frame blocks; the minimum lower bound decides | B6 | Captures periodic dependence that no block length captures |
| CL-08 | C6 repaired and demoted to exploratory; H2 withdrawn | B7 | No decision rests on C6 |
| CL-09 | C0b = circular-shift chance baseline with phase restriction | B8 | Collapse is fold-calibrated |
| CL-10 | Single validity chain collapse > motion > saturated; q9 rounding on exact rationals | B9 | Deterministic labels and boundaries |
| CL-11 | Final outcome I (inconclusive) replaces "B mapped to C" | B9, clarity | Inconclusive is not reported as null |
| CL-12 | Validation constants recomputed per coreset seed; Stage 3 re-verifies them | New | Removes an undefined choice in v1.1 |
| CL-13 | k_t = 25 at m_t = 0; g_p range capped at N_s; float64 accumulation | New | Removes undefined computations |
| CL-14 | Coresets for all seeds built once in Stage 2; seeds 1 and 2 scored in the same Stage 3 pass | New | No human decision point between seeds |
| CL-15 | "PatchCore-derived" naming; seeding difference stated; commit pinned | Audit | Honest fidelity claim |
| CL-16 | Lag-perm misalignment corrected to >= floor(\|dx\| / 8) cells (4 at 38 px) | Audit | Correct control description |
| CL-17 | Sensitivity S2 (carry-over), S3/S4 (track concentration) added | Audit | Concentration and carry-over visible next to results |
| CL-18 | Scientific question: decomposition clause moved out of the confirmatory question | B7 | Confirmatory scope matches the decision |
