# Motion-aligned anomaly detection on knitted-fabric video: a preregistered pilot, stopped at validation

**Technical note.** Tinon Turja Majumder, October 2026. Not peer-reviewed.
Repository: <https://github.com/Tinonturja/tsfabrics_alignment_pilot>. Decision log: `docs/decisions/DECISION_LOG.md`.

> **Status in one line.** The pilot stopped at Stage 2 (validation) under its own preregistered stop rule. Stage 3
> (the test run) never started. No test-scenario label, anomaly map, score or metric was ever computed, so this
> note reports **no result about the research question**.

## Summary

Unsupervised (normal-only) defect detectors such as PatchCore assume a still part under a still camera. On a
knitting machine the fabric moves between frames. This pilot asked whether averaging anomaly maps at the same
physical fabric location, after aligning frames to the measured fabric motion, changes false alarms and missed
defects compared with single-frame scores, score smoothing and unaligned map averaging. The design was frozen and
hashed before any code ran, the test scenarios were locked behind an access gate, and the work ran in three sealed
stages on Kaggle. Stage 1 (code and reference tests) passed. Stage 2 failed twice at its first phase. The second
failure was a direction check on motion estimates: on the validation fabric, the pattern repeats about every 85 px
and the fabric moves about 86 px per frame, so a correct shift and its reverse look almost equally wrong, and the
check passed on 112 of 200 frame pairs where 190 were required. Under the stop clause written into amendment v1.2.2,
no further change was allowed and the pilot ended there.

## 1. Question

Does averaging normal-only anomaly evidence at corresponding physical fabric locations (variant V4, aligned by
measured motion) change false alarms and missed defects relative to:

- V0, single-frame scores;
- V1, temporal smoothing of the frame score;
- V2, map averaging without alignment;
- two controls that keep everything except the correspondence (reversed alignment and lag permutation)?

The controls exist so that any gain from V4 can be attributed to alignment and not to averaging as such.

## 2. Data

TSFabrics (Ni et al., 2026, *Scientific Data*, DOI 10.1038/s41597-026-06748-9) is a public video dataset of knitted
fabric on a circular knitting machine: 93,196 frames in 22 scenarios. The pilot uses two leave-one-group-out folds
built from fabric groups so that no fabric appears on both sides of a split:

| Fold | Test scenarios | Test frames | Strict defect passes |
|---|---|---|---|
| A-G1 | 5 | 43,744 | 162 |
| A-G4 | 3 | 24,916 | 99 |

Each fold has a 300-frame normal bank (training side) and validates on all 1,212 frames of `T1_S164_I199_1`, a
scenario that is a test scenario in neither fold. No images or masks are redistributed in this repository.

## 3. Method in brief

| Part | Choice |
|---|---|
| Detector | PatchCore-derived: ImageNet-pretrained WRN-50-2 features, 3x3 patch neighbourhoods, coreset memory bank, nearest-neighbour distance as the anomaly score; official PatchCore files pinned byte-for-byte |
| Motion | Phase correlation between consecutive frames; each estimate is classed reliable, held or unknown by a consistency band and a reliability threshold tau_r chosen on training-side scenarios only |
| Motion validity | A fold is motion-invalid if tau_r is undefined or more than 5% of its test frames are motion-unknown; V4 then falls back to V2 |
| Statistics | Exact rational arithmetic for every decision quantity; cluster bootstrap over rotation-phase clusters; three coreset seeds; a decision machine with named outcomes, fixed before scoring |

## 4. How the study was protected from its author

| Safeguard | Implementation |
|---|---|
| Preregistration | `PREREGISTRATION.md` (v1.2) frozen 27 Sep 2026 and hashed; every constant in one YAML file whose hash goes into every report |
| Amendments | Only by a dated, hashed, audited text adopted before new data is read, labelled as preregistered or post-diagnostic (v1.2.1, v1.2.2) |
| Synthetic calibration | Statistical procedures and the motion candidate were tested on generated data with known truth before real data |
| Sealed stages | Stage 1 opens no image; Stage 2 never scores a test frame; Stage 2 refuses to start unless the Stage 1 report on disk has the recorded SHA-256 |
| Test lock | Every image read goes through a gate that refuses test-scenario frames and logs reads by purpose |
| Code identity | A files fingerprint of the running tree is compared with the committed tree on every run |
| Failure record | Failed runs kept in `audit/*_FAIL/`; corrections made by erratum entries; Git history never rewritten |

## 5. What happened

| Date (2026) | Event | Log |
|---|---|---|
| 27 Sep | Research Gate v1.2 frozen | DL-0001 |
| 30 Sep to 1 Oct | Calibration of the chance test failed, was diagnosed under a pre-hashed addendum, and fixed by amendment v1.2.1 | DL-0002 to DL-0007 |
| 4 Oct | Stage 1 PASS on Kaggle (53 of 53 tests) | DL-0012 |
| 6 Oct | Stage 2 run 1 FAIL at phase A: A-G4 motion-invalid (best consistency 93.6%, below the 95% condition); direction check 92 of 200 on `T1_S164_I199_1`, whose motion estimates partly alias | DL-0015 |
| 6 Oct | Amendment v1.2.2 adopted (post-diagnostic, not preregistered): a new motion candidate M1, revised numerical tolerances, a new direction check on `T1_S164_I192_1` and `T1_S164_I193_1`, and a stop clause | DL-0016 |
| 6 Oct | M1 failed its synthetic calibration (14 of 16 criteria); not adopted, frozen motion rule kept | DL-0017 |
| 7 Oct | Stage 1 under v1.2.2: one over-strict unit test failed (bit-identity across chunk sizes under BLAS rounding); replaced by a tolerance test plus a batch-composition test; then PASS, 144 of 144 | DL-0020 to DL-0022 |
| 7 Oct | Stage 2 rerun FAIL at phase A; pilot stopped at Stage 2 | DL-0024 |

Stage 2 rerun, fold A-G1: tau_r = 0.00; validation statuses 381 reliable, 633 held, 198 unknown. Fold A-G4: tau_r
undefined (motion-invalid). All 13 raw motion files were bit-identical to run 1.

## 6. Why it stopped

The direction check (AT-06b) took 200 consecutive reliable frame pairs (t - 1, t) from `T1_S164_I192_1`, chosen from
motion statuses alone and hashed before any image was read. For each pair it warped the previous frame by the
measured shift U (in 8 px cells) and by -U, and counted the pair as holding if U gave the lower mean squared error.
The pass mark was 190 of 200. The result was 112.

The explanation, obtained after the verdict and not used to change anything:

- The measured shift was U = 11 cells for 190 pairs (10 for 9, 12 for 1), about 86 px per frame.
- The S164 fabric repeats about every 85 px. Consecutive frames therefore look almost unchanged, and warping by
  +U or -U (about one repeat either way) is nearly equally wrong.
- The unshifted previous frame matched the current frame better than either warp: median MSE ratio to zero shift
  was 1.34 for U and 1.41 for -U.
- The measured direction is not reversed: U beat -U in 112 pairs and had the lower median MSE, and the sign tests
  on synthetic textures pass. The check simply cannot see direction on this fabric.

The scenarios chosen for the check in v1.2.2 are the same fabric at the same speed as the one they replaced. Neither
the amendment nor its audit compared the fabric's pattern period with its per-frame displacement. That omission is
the cause of the failure.

## 7. Classification

| Kind | Finding |
|---|---|
| Protocol | Worked as declared: the stop rule fired as written. One check in v1.2.2 was unable to measure what it was meant to on this fabric |
| Implementation | No defect found: the committed code ran, motion reproduced bit for bit, the synthetic direction tests pass, no test frame was read |
| Science | No result. The alignment hypothesis was not tested; this is not evidence for or against it |

## 8. What a follow-up study would need

These are directions, not commitments, and any of them is a new study with its own preregistration:

- Measure the pattern period of every candidate validation scenario against its per-frame displacement before
  choosing scenarios for any motion check.
- Check motion direction on frames with synthetic shifts of known size, where the answer is known by construction.
- Ask a question that does not depend on motion at all, such as how a normal-only detector behaves when machine
  speed or lighting changes.
- Disclose that the raw phase-correlation traces of all 13 pilot scenarios have been seen. Test labels, maps,
  scores and metrics have not.

## 9. Records

| Item | Location | SHA-256 (first 8) |
|---|---|---|
| Final status report | `docs/stage2/STAGE2_RERUN_AND_PILOT_STATUS.md` | |
| Amendment v1.2.2 | `docs/stage2/AMENDMENT_v1.2.2_PROTOCOL.md` | `276fe983` |
| M1 calibration | `calibration/v1_2_2_m1/` | result `7a82d069` |
| Stage 1 (v1.2.2) record | `audit/stage1_kaggle_v1_2_2/` | report `eb34435b` |
| Stage 2 rerun record | `audit/stage2_kaggle_v1_2_2_FAIL/` | report `1164258f` |
| Decision log | `docs/decisions/DECISION_LOG.md` | |

Dataset: Ni et al., TSFabrics, *Scientific Data* (2026), DOI 10.1038/s41597-026-06748-9.
