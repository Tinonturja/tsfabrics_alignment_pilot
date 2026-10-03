# C0b calibration report

Pre-registered calibration of the v1.2 chance baseline (C0b) on synthetic, label-independent score traces. No TSFabrics image, map or score was used. The outcome led to amendment v1.2.1 (`PREREGISTRATION_AMENDMENT_v1.2.1.md`).

# Phase 1. C0b calibration

Labels: **[FACT]** is a computed or verified result. **[INFERENCE]** is an argument. **[RECOMMENDATION]** is a proposed action.

## 1.1 What C0b is for, and why it had to be calibrated

**[FACT] C0b (v1.2 section 19)** asks one question: *is V0 better than a detector with the same score dynamics but no information about where defects are?*

- It circularly shifts V0's frame-score trace within each test scenario 200 times, recomputes P3 each time, and counts k = number of shifted P3 values >= the observed P3.
- The fold is **collapsed iff k >= 10**.
- A collapsed fold sets the validity state to `collapse`, which routes the pilot to outcome **G** ("detector collapse; pivot to the condition-shift question").

**[FACT] What v1.2 claimed:** "By construction, a detector with no defect information escapes collapse with probability of about 5%." It also said the phase restriction "costs nothing".

**[INFERENCE] Why this needed checking.** "By construction" is only true if the observed trace is exchangeable with the 200 shifted traces. That holds for independent scores. It is not guaranteed for scores that are strongly autocorrelated, and V0 will be: consecutive frames overlap by 80% to 95% of their content, and lighting and tension drift slowly. The v1.2 test (one random trace per fold collapsed) could not detect a rate problem; it only showed that one example behaved.

**[INFERENCE] Why it matters for the science.** If an uninformative detector escapes C0b, the pilot proceeds to the V4 comparisons. With no signal in the maps, those comparisons will most likely come out null. The pilot would then report "alignment does not help" when the true answer is "the detector saw nothing". That is exactly the misdirected conclusion the gate exists to prevent.

## 1.2 Design (pre-specified before any trace was generated)

**Protocol file:** `PROTOCOL.md`, written 2026-09-30 17:14 UTC, SHA-256 `d537d67c...8544be`. After the first FAILs, `ADDENDUM-1.md` was written **before any diagnostic or candidate run** (SHA-256 `30ae3d23...ce314a4b1`).

**Inputs used, and only these:**

- the frozen pilot pass layout CSV (window positions, N_f frames, tracks), with windows built from the scenario-median k. This is an approximation of the adaptive K_t and is stated as such;
- the frozen rotation periods P_s;
- synthetic score traces generated independently of the labels;
- the frozen v1.2 rule, implemented exactly.

**The key simplification [FACT, proven in the protocol].** P3 depends only on the *order* of the scores: thresholds are the distinct score values and an alarm is score >= tau. So the marginal distribution of the scores is irrelevant. Only temporal dependence and ties can change the false-pass rate. The null families therefore vary dependence, non-stationarity, periodicity and ties.

**Null families** (all independent of the labels):

| ID | Model | What real behaviour it stands for |
|---|---|---|
| N1 | iid Gaussian | Sanity check: exact exchangeability |
| N2 | AR(1), phi = 0.9 | Moderate frame-to-frame correlation |
| N3 | AR(1), phi = 0.99 | Strong correlation (overlapping frames) |
| N4 | AR(1), phi = 0.999 + small noise | Slow drift (lighting, tension, temperature) |
| N5 | AR(0.9) + per-scenario level N(0, 2^2) | Different mean score per scenario |
| N6 | AR(0.9) + fixed random profile with period P_s | Rotation-periodic structure (cutline, seams) |
| N7 | AR(0.9) + linear trend, total change 2 sd | Warm-up or monotone drift within a scenario |
| N8 | AR(0.95) + level + periodic + drift | All of the above together |
| N9 | iid rounded to about 20 levels | Heavy ties |

**How many traces, and why 2,000.** For a true rate of 5%, 2,000 traces give a 95% Clopper-Pearson interval of about +/- 1 percentage point. The decision rule per (family, fold) was:

- **PASS** if the upper 95% bound <= 7.5%;
- **FAIL** if the lower bound > 7.5%;
- otherwise **INDETERMINATE**, and n is doubled once.

If the true rate is 5%, P(upper bound <= 7.5%) > 0.99, so a correct rule almost never fails by chance. 7.5% is 1.5 times the design level, a tolerance chosen before any result.

**C0b is calibrated only if all 18 cells PASS.**

**Correctness of the computation [FACT].**

- A fast integer kernel computes P3 for shifted traces. It was checked against the exact Fraction reference (`ref_metrics.py`) on the real layout: **8 of 8 cases equal exactly**, both folds, shifted and unshifted, iid and smoothed traces.
- Reproducibility: re-running N1 / A-G1 through a second script gave the identical count (95 of 2,000).

## 1.3 Primary result: the v1.2 rule

**[FACT] n = 2,000 per cell (n = 4,000 where doubled). Design level 4.975%.**

| Family | A-G1 false-pass rate [95% CI] | Verdict | A-G4 false-pass rate [95% CI] | Verdict |
|---|---|---|---|---|
| N1 iid | 4.75% [3.86, 5.78] | PASS | 6.15% [5.14, 7.29] | PASS |
| N2 AR 0.9 | 6.15% [5.14, 7.29] | PASS | 5.50% [4.54, 6.59] | PASS |
| N3 AR 0.99 | **10.25%** [8.95, 11.66] | **FAIL** | 6.10% [5.09, 7.24] | PASS |
| N4 drift | **17.20%** [15.57, 18.93] | **FAIL** | **9.95%** [8.67, 11.35] | **FAIL** |
| N5 levels | 5.70% [4.72, 6.81] | PASS | 5.20% [4.27, 6.27] | PASS |
| N6 periodic | **8.85%** [7.64, 10.18] | **FAIL** | 7.42% [6.63, 8.28] (n=4,000) | INDETERMINATE |
| N7 trend | **12.05%** [10.65, 13.56] | **FAIL** | 7.52% [6.73, 8.39] (n=4,000) | INDETERMINATE |
| N8 composite | **10.95%** [9.61, 12.40] | **FAIL** | 7.03% [6.25, 7.86] (n=4,000) | INDETERMINATE |
| N9 ties | 5.50% [4.54, 6.59] | PASS | 5.45% [4.50, 6.54] | PASS |

**Reading it.**

- **6 FAIL, 3 INDETERMINATE, 9 PASS. C0b as frozen is not calibrated.**
- The failures grow with the length of dependence: iid is fine, AR 0.9 is borderline, AR 0.99 and drift fail. A-G1 is worse than A-G4. The reason was not tested; one plausible reason is its short scenario (617 frames), where the offset band is narrow in absolute terms.
- **Both tails are inflated**, not only one. Under exchangeability, the observed trace should land below all 200 shifts (k = 200) about 0.5% of the time. For N4 in A-G1 it did so 7.45% of the time. A too-narrow null distribution produces this pattern; a simple one-sided bias does not.

## 1.4 Diagnosis: which component fails

**[FACT] Diagnostics** (D1, D2 pre-registered in PROTOCOL.md; D3, D4 pre-registered in ADDENDUM-1):

| Diagnostic | What it isolates | Result |
|---|---|---|
| **D3.** Seam-free nulls (circular-stationary AR, no wrap discontinuity exists) with the **v1.2 offsets** | If it fails, the seam is not the cause | **FAIL:** A-G1 10.7% (phi 0.99) and **16.1%** (phi 0.999); A-G4 6.3% (PASS) and 9.8% (FAIL) |
| **D4.** Same seam-free nulls with **offsets uniform on the whole scenario** | Theory says exact | **PASS:** 4.8%, 4.5%, 4.6%, 4.5% |
| **D2.** v1.2 band [N/4, 3N/4] **without** the phase restriction (A-G1, n = 1,000) | Is it the band or the phase rule? | N3 10.1% FAIL; N4 16.5% FAIL; N7 11.0% FAIL; N8 8.5% INDET; **N6 4.9% PASS** |
| **D1.** Observed trace also given one random v1.2 offset (A-G1, n = 1,000) | Positive control: the observed becomes an iid draw from the same set | All PASS (4.0% to 5.3%) |

**Conclusions [INFERENCE, supported by the table].**

1. **The circular shift itself is not the problem.** D3 fails with no seam at all; D4 and the amendment pass with the same shift. The wrap seam contributes at most a small amount (see 1.6).
2. **The offset band [N_s/4, 3N_s/4] causes the failures under autocorrelation, drift and trend** (D2 still fails without the phase rule).
3. **The phase restriction causes the failure under rotation-periodic nulls** (D2 passes N6 once it is removed). So v1.2's "the restriction costs nothing" was wrong.
4. **Mechanism.** All 200 offsets sit in the middle of the scenario, so under long-range dependence the 200 shifted traces resemble *each other* much more than they resemble the observed trace, which sits at offset 0, far from all of them. The null distribution is then too narrow, and the observed value falls in either tail too often. A set of transformations that is not a group, and that excludes the neighbourhood of the identity, does not give an exchangeable reference set.
5. **Primary theory (verified).** Hemerik and Goeman (2018, *TEST* 27(4):811-825) prove that a test using *random* transformations is exact when they are drawn from a group under which the null distribution is invariant. Ramdas, Barber, Candès and Tibshirani (2023, *Sankhya A* 85:1156-1177) show that using an arbitrary subset that is not a subgroup gives invalid p-values unless a random correction is added. Both describe this situation exactly. The bibliographic records and abstracts were verified; the proofs were not re-derived.

**Origin of the error.** The restriction was introduced in v1.2 (fix B8) to keep shifts "far from realignment". Its effect on validity was not checked, and the final pre-registration audit accepted the "by construction" claim. The pre-registered calibration caught it.

## 1.5 The amendment candidate A1 and its result

**[FACT] A1 (specified in ADDENDUM-1 before it was run).** For each scenario, in lexicographic order, draw 200 offsets with `rng.integers(0, N_s, 200)` from the same generator `PCG64([20260925, fold_index, seed_index])`. Offsets may be 0 for a scenario. Everything else is unchanged.

**Primary result under A1** (n = 2,000 per cell):

| Family | A-G1 [95% CI] | A-G4 [95% CI] |
|---|---|---|
| N1 iid | 4.25% [3.41, 5.23] | 5.50% [4.54, 6.59] |
| N2 AR 0.9 | 4.85% [3.95, 5.88] | 4.85% [3.95, 5.88] |
| N3 AR 0.99 | 4.20% [3.36, 5.17] | 4.15% [3.32, 5.12] |
| N4 drift | 4.55% [3.68, 5.56] | 4.70% [3.81, 5.72] |
| N5 levels | 4.30% [3.45, 5.28] | 4.70% [3.81, 5.72] |
| N6 periodic | 5.45% [4.50, 6.54] | 5.75% [4.77, 6.86] |
| N7 trend | 5.45% [4.50, 6.54] | 3.20% [2.47, 4.07] |
| N8 composite | 5.05% [4.13, 6.10] | 4.35% [3.50, 5.34] |
| N9 ties | 4.90% [4.00, 5.94] | 5.55% [4.59, 6.65] |

- **All 18 cells PASS.** Highest upper bound 6.86%.
- **Pooled over all 36,000 traces: 4.76% [4.55%, 4.99%]**, against a design level of 4.975%. Slightly conservative, as expected when ties and near-zero offsets are possible.

**Secondary checks (pre-registered as not decision-relevant).**

- Offset seeds 1 and 2 (n = 1,000; N1, N6, N8): 9 of 12 cells PASS. Three were INDETERMINATE: A-G4 N6 at seeds 1 and 2 (6.6%, 7.0%) and A-G1 N8 at seed 2 (5.9%).
- Doubling A-G4 N6 to n = 2,000: seed 1 5.85% [4.86, 6.97] PASS; seed 2 6.15% [5.14, 7.29] PASS.
- **Not pre-registered, run because of those INDETERMINATE cells:** the rate averaged over 20 further offset seeds (3 to 22), 200 traces each:
  - A-G4 N6 periodic: **6.20% [5.47, 6.99]**. Above 5%, within the 7.5% tolerance.
  - A-G1 N6 periodic: 5.63% [4.93, 6.38].
  - A-G4 N1 iid: 5.30% [4.63, 6.04].
  - A-G4 N8 composite: 2.95% [2.45, 3.52] (conservative).

**Power, the cost of A1 [FACT].** Synthetic weak signal: AR(0.9) noise plus a mean shift delta inside every pass window, n = 500.

| Signal | v1.2 rule: fraction not collapsed | A1: fraction not collapsed |
|---|---|---|
| A-G1, delta = 0.25 sd | 65.6% | 63.6% |
| A-G1, delta = 0.50 sd | 99.6% | 99.4% |
| A-G4, delta = 0.25 sd | 80.0% | 79.2% |
| A-G4, delta = 0.50 sd | 100% | 100% |

A1 loses at most 2 percentage points of power, and part of v1.2's apparent power was its inflated size.

## 1.6 The residual weakness, stated plainly

- **[INFERENCE]** The remaining excess under rotation-periodic nulls comes from the wrap seam. When N_s is not a whole number of rotations, a shifted trace carries a periodic component whose phase jumps once at the seam, so it is a mixture of two phases, while the observed trace has one pure phase.
- **Size:** about 6% instead of 5% in A-G4 for a periodic component as large as the AR noise. Smaller in A-G1.
- **Possible fix:** evaluate the chance test on each scenario trimmed to a whole number of rotations. This is **not** adopted in v1.2.1: it changes the observed statistic (frames are dropped), it is a bigger change than the failure justifies, and the pre-registered criterion is met.
- **Disclosure required in the paper:** "C0b's false-pass rate was calibrated on nine synthetic null families: pooled 4.8%; highest single-condition estimate 6.2% (strongly periodic null, A-G4)."

## 1.7 Decision: v1.2 cannot remain frozen. Adopt v1.2.1.

**[RECOMMENDATION] The complete amendment, and nothing more:**

| v1.2 location | v1.2 text | v1.2.1 text |
|---|---|---|
| Section 19, "Allowed offsets for scenario s" | Integers d with ceil(N_s/4) <= d <= floor(3N_s/4), d != 0, and ceil(P_s/4) <= (d mod P_s) <= floor(3P_s/4) | All integers d with 0 <= d <= N_s - 1 |
| Section 19, "RNG" | "each offset is uniform over the allowed set via `integers(0, n_allowed)`" | "each offset is `integers(0, N_s)`; for each scenario in lexicographic order, the 200 offsets are drawn as one call `integers(0, N_s, 200)`" |
| Section 19, "Why it is appropriate" | "...The phase restriction keeps every recurrence at least a quarter-rotation away..." and "The restriction costs nothing" | Delete both. Add: "Offsets are uniform on the cyclic group of each scenario, which makes the random-shift test exact under circular stationarity (Hemerik and Goeman 2018). A restricted offset band was shown by calibration to inflate the false-pass rate to up to 17% (calibration report, 2026-09-30)." |
| Section 19, "Error rate" | "By construction ... about 5%" | "Calibrated on nine synthetic null families: pooled 4.8% [4.5, 5.0]; highest single condition 6.2% (strongly rotation-periodic null, A-G4, averaged over 20 offset seeds)." |
| AT-15 | "all lie in the allowed set; none is 0" | "all lie in [0, N_s - 1]; the generator reproduces `calibration/c0b/amend.py` exactly for seeds 0 to 2" |
| Section 27 (declared limitations) | none for C0b | Add the residual periodic excess from 1.6 |

**Unchanged:** 200 shifts; the seed tuple; P3 as the statistic; the k >= 10 collapse rule; the validity chain; the decision machine; every threshold in C1 to C7.

**Why this is not post-hoc tuning.**

1. **No outcome data exist.** No TSFabrics test image, map or score has been computed. The amendment cannot be steered towards a preferred result because there is no result.
2. **It was triggered by a pre-registered FAIL**, exactly as PROTOCOL.md requires ("any change must be a dated v1.2.1 justified by a FAIL").
3. **The candidate was specified before it was run** (ADDENDUM-1 hash), and it was the only candidate. There was no search over alternatives.
4. **It comes from theory, not from fitting.** Uniform draws from the group are the textbook condition for exactness. The amendment removes a restriction; it adds no tunable constant.
5. **It could have failed.** It was held to the same 18-cell criterion as v1.2.
6. **It does not make the pilot easier to pass.** A1 is slightly *harder* for a real detector to pass than v1.2 (power 63.6% vs. 65.6% for a weak signal). It only removes false passes.

**Before proceeding to code:** write the amendment as `PREREGISTRATION_AMENDMENT_v1.2.1.md`, hash it, and log it (DL-0003). Until then, v1.2's section 19 must not be implemented as written.
