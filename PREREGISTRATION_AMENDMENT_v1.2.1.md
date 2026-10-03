# TSFabrics Research Gate: Amendment v1.2.1

**Status:** ADOPTED by Tinon Turja Majumder on 2026-10-01 (UTC).
**Amends:** Research Gate v1.2 (2026-09-27).

- `gate_v12.md` SHA-256: `182df443b29e8b5ee1922de61219871c1a6e052f538fd8ef1c4b4466db4a70dd`
- `TSFabrics_Research_Gate_v1.2_2026-09-27.pdf` SHA-256: `146000d19fb0299c11a90084816b25cc5ddec5440834a20d5433313582d07986`

**Scope:** section 19 (chance baseline, C0b), acceptance test AT-15, and section 27 (limitations). **Nothing else in v1.2 changes.**

## A. Data-access declaration

At the time of adoption:

- no TSFabrics test-scenario image, anomaly map or score had been computed or viewed;
- no bank or validation features had been computed;
- no pipeline code existed.

The amendment was justified and evaluated using synthetic, label-independent score traces on the frozen pass layout only.

## B. Trigger and evidence

The pre-registered C0b calibration found that the v1.2 rule is not calibrated.

- **Protocol:** `calibration/c0b/PROTOCOL.md`, SHA-256 `d537d67c78e1861113e3376f3cdf2652fe56bcb2f5d064d13d1dfbf7858544be`.
- **Results under the v1.2 rule:**
  - 6 of 18 (family, fold) cells FAIL; 3 remain INDETERMINATE after n was doubled.
  - False-pass rates reach 17.2% (95% CI 15.6% to 18.9%) against a design level of 4.975%.
- **Diagnosis and candidate:** pre-specified in `calibration/c0b/ADDENDUM-1.md` (SHA-256 `30ae3d2321f9bef5af4ad1f8e1c20bb24e6900722990eff3aecc2ebce314a4b1`) before any diagnostic or candidate was run.
  - The failure is caused by the restricted offset set, not by the circular shift: seam-free nulls fail with the v1.2 offsets and pass with uniform offsets.
- **Candidate A1 (adopted here):**
  - 18 of 18 cells PASS.
  - Pooled false-pass rate 4.76% (95% CI 4.55% to 4.99%).
- **Full report:** `TSFabrics_C0b_Calibration_and_Novelty_Audit_2026-09-30.pdf`, Phase 1.
- **Result files:** `results/c0b_primary_all_n2000.csv` (SHA-256 `5aa0361d61ac1c41e7432b76639f6801d47609e6cf9156c3c1eda7365afda31f`) and `results/A1_uniform.csv` (SHA-256 `f453d865c85f34f4a4bbbacc87d10407bee184b10cc415ba2a392bf00f64fc81`).

## C. Changes

### C1. Section 19, row "Allowed offsets for scenario s"

**v1.2 (struck):**

> Integers d with ceil(N_s / 4) <= d <= floor(3 N_s / 4), d != 0, **and** ceil(P_s / 4) <= (d mod P_s) <= floor(3 P_s / 4). The phase restriction keeps every recurrence at least a quarter-rotation away from realignment.

**v1.2.1:**

> All integers d with 0 <= d <= N_s - 1 (the full cyclic group of the scenario). No band and no phase restriction. d = 0 is permitted for an individual scenario.

### C2. Section 19, row "RNG"

**v1.2 (struck):**

> `numpy.random.Generator(PCG64([20260925, fold_index, seed_index]))`; scenarios in lexicographic order; each offset is uniform over the allowed set via `integers(0, n_allowed)`.

**v1.2.1:**

> `rng = numpy.random.Generator(numpy.random.PCG64([20260925, fold_index, seed_index]))`, with fold_index 0 = A-G1 and 1 = A-G4. For each test scenario in lexicographic order, draw its 200 offsets in one call, `rng.integers(0, N_s, 200)`. Stack the per-scenario vectors as columns to form a 200 x S integer array; row b is shift b.

### C3. Section 19, "Why it is appropriate"

- **Delete** the sentence about the phase restriction.
- **Delete** "Without the phase restriction, the null maximum rose from 0.263 to 0.298 for random V0 in A-G4. The restriction costs nothing."
- **Add:**

> Offsets are drawn uniformly from the cyclic group of each scenario. A test based on random transformations drawn uniformly from a group is exact when the null distribution is invariant under that group (Hemerik and Goeman 2018, TEST 27(4):811-825). A restricted band of offsets is not a group, and calibration showed it inflates the false-pass rate up to 17.2% under autocorrelated, drifting, trending and periodic null traces.

### C4. Section 19, "Tested" table

The three rows (random, weak-signal and strong-signal V0) were computed with the v1.2 offsets. They are **superseded**. They will be recomputed under v1.2.1 as part of AT-15 in Stage 1, and the new values recorded in the Stage 1 report.

### C5. Section 19, "Error rate"

**v1.2 (struck):**

> By construction, a detector with no defect information escapes collapse with probability of about 5%.

**v1.2.1:**

> Calibrated on nine synthetic null families (iid, AR 0.9, AR 0.99, slow drift, scenario levels, rotation-periodic, trend, composite, ties) on the frozen layout of both folds, n = 2,000 per cell: pooled false-pass rate 4.76% (95% CI 4.55% to 4.99%); every cell's 95% upper bound <= 6.86%. Highest single-condition estimate: 6.2% (95% CI 5.5% to 7.0%), for a strongly rotation-periodic null in A-G4, averaged over 20 offset seeds (exploratory, not pre-registered).

### C6. AT-15

**v1.2 (struck):**

> Offsets reproduce from the seed; all lie in the allowed set; none is 0; on the synthetic real-layout cases, random V0 collapses and strong V0 does not.

**v1.2.1:**

> Offsets reproduce from the seed, and all lie in [0, N_s - 1]. The SHA-256 of the 200 x S int64 offset array (C order) equals the fixture below for seeds 0, 1 and 2 in both folds. On the synthetic real-layout cases, random V0 collapses and strong V0 does not. The implementation's false-pass count on calibration cell (N1_iid, A-G1, n = 200, trace seeds `[777, 0, 0, i, 0]`) equals the count produced by `calibration/c0b/amend.py` (6 of 200 not collapsed; results/at15_fixture.csv).

**AT-15 fixture** (numpy 2.4.4; recorded 2026-10-01):

| Fold | Seed | SHA-256 of offsets |
|---|---|---|
| A-G1 | 0 | `2182b12659c5608cf72e99b01a1fbd2bd1ac35c979d7fd913619d55b3bd2138b` |
| A-G1 | 1 | `894acd0c45f65322a93192ced2d36ce7da9c89b409af3efef4804adbc6294a38` |
| A-G1 | 2 | `519638b9d8b3a66564b67c5aaaf5e76b66784a6b7f96c7defdd0c3e98ef67155` |
| A-G4 | 0 | `f3c86cd13135f966319b4b183e0af6baa80b267b028e9ef894d7e4dc472a979c` |
| A-G4 | 1 | `65aaaf6fd6145b97607d00815cd000e3444d50a177a35eeccb779b3db02940ac` |
| A-G4 | 2 | `28f1fc386a2257e1e08e8044621217d381dd0b9b7864af9e5f9d5140bce49962` |

First three rows of the seed-0 offsets, as a hand check:

- **A-G1** (scenarios T1_S148_I108_1, T1_S148_I108_2, T1_S174_I108_1, T1_S174_I111_1, T1_S177_I108_1): [2469, 118, 286, 6833, 16396], [519, 309, 148, 14196, 10598], [2010, 1080, 486, 10825, 1055].
- **A-G4** (T1_S478_I118_1, T1_S478_I118_2, T1_S555_I117_1): [1613, 415, 13001], [2073, 2449, 8417], [221, 519, 140].

**If a different numpy version changes PCG64 `integers` output, AT-15 fails and the Stage 3 environment must pin numpy 2.4.4.**

### C7. Section 27, new limitation 11

> **C0b residual periodic excess.** When a scenario does not contain a whole number of rotations, a circular shift gives the trace's rotation-periodic component one phase jump. Under a strongly periodic synthetic null this raised the false-pass rate to about 6.2% in A-G4 (versus 4.975% design). Evaluating C0b on whole-rotation-trimmed scenarios would remove it but changes the observed statistic. It was not adopted. The lag-P_s autocorrelation of the real V0 trace will be reported descriptively.

## D. Unchanged (explicitly)

- 200 shifts per fold and coreset seed.
- The seed tuple [20260925, fold_index, seed_index].
- np.roll semantics within each scenario.
- P3 as the chance statistic, with exact rational comparison.
- The collapse rule k >= 10 (p = (1 + k) / 201 > 0.05).
- The validity chain (collapse > motion > saturated).
- The outcome machine.
- Every C1 to C7 threshold.
- All other acceptance tests.
- The three-stage protocol.

## E. Why this is not post-hoc tuning

1. No outcome data existed (section A).
2. The change was triggered by a FAIL under a protocol that was hashed before any trace was generated.
3. The candidate was specified and hashed before it was run, and it was the only candidate.
4. It follows from a published exactness condition. It removes a restriction and adds no tunable constant.
5. It was held to the same 18-cell criterion that v1.2 failed.
6. It makes C0b slightly harder for an informative detector to pass. Synthetic weak-signal power: 63.6% versus 65.6% (A-G1), 79.2% versus 80.0% (A-G4).

## F. Decision log entry

**DL-0007 (2026-10-01).** v1.2.1 adopted, as above. Next allowed action: Stage 1 implementation against v1.2 + v1.2.1.
