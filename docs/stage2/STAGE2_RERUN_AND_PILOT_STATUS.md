# Stage 2 rerun under v1.2.2 and final pilot status

**Status: the pilot is stopped at Stage 2** (amendment v1.2.2, section 5; DL-0024). Stage 3 was not started. No
test-scenario label, anomaly map, detector score or metric was ever computed.

## 1. The run of record

| Item | Value |
|---|---|
| Kaggle notebook | `notebookddbe9e9387`, version 2 (run `355999796`), GPU Tesla T4, 2026-10-07 08:09 to 08:41 UTC |
| Earlier attempt | version 1 (run `355999216`) did not start: Kaggle could not mount the TSFabrics dataset; no code ran |
| Inputs | repository dataset version 5 (commit `cbea7d1`), TSFabrics dataset version 1 |
| Environment | Python 3.13.15, numpy 2.4.4, torch 2.11.0+cu128, torchvision 0.26.0+cu128, timm 1.0.29, faiss 1.15.1, CUDA 12.8 |
| Files fingerprint | `cb17b0cae1723f03366cbb686a4f2597788d867926be7ff008bf5d69d5f6fe10` (equals the committed tree) |
| Preconditions | none failed: v1.2.2 config and amendment hashes, Stage 1 record `eb34435b...` (DL-0022), DL-0012 bank |
| Smoke run (not the record) | every phase ran; AT-01, AT-02, AT-03, AT-04a, AT-04b passed; AT-06b not applicable (60 motion frames) |
| Phase 0 | 61 unit tests passed |
| Phase A | **FAIL** |
| Phases B to E | not run (the runner stops at the first failed phase) |
| Report SHA-256 | `1164258f2137a713c430e0ddcfe58a9bccbdbe5d65f8face68b864ba58a2bcad` |
| Record zip SHA-256 | `4bea162bc39e7c515c8655305f90921ec54434bcd8495c81c1d733c7c6ca9d09` (`audit/stage2_kaggle_v1_2_2_FAIL/`) |
| Data-access violations | none |

## 2. Results

| Quantity | A-G1 | A-G4 |
|---|---|---|
| tau_r (frozen rule) | 0.00 (31,711 of 31,791 pairs at tau, 30,214 consistent) | undefined: fold motion-invalid |
| Validation statuses | 381 reliable, 633 held, 198 unknown | 1,212 unknown |
| AT-06b (v1.2.2 C4) | **FAIL: 112 of 200 pairs hold (190 required)** | not applicable |

AT-06b selection (written and hashed before any image was read, `b98e16ca...`): rule 1, the earliest run of 200
consecutive reliable frames in `T1_S164_I192_1`, pairs (t - 1, t) for t = 2 to 201. Reliable frames: 1,018 of 1,020
in I192, 1,030 of 1,037 in I193. Shift U = 11 cells for 190 pairs, 10 for 9, 12 for 1.

**Reproducibility (v1.2.2 section 5 step 4).** All 13 raw motion files are bit-identical to Stage 2 run 1 (SHA-256
compared file by file), and both folds' tau_r records equal run 1's. The rerun's tau_r is the one of record.

## 3. Consequence under the adopted protocol

v1.2.2 section 5: "No further amendments of section 7, AT-03, AT-04b or AT-06b are permitted in this pilot. If any of
them fails after v1.2.2, Stage 3 does not start. The pilot is then reported as stopped at Stage 2, with the failure
recorded." This agrees with DL-0023 (Stage 3 was not to be run in any case, because with A-G4 motion-invalid the
reachable final outcomes of section 22 were only I, M and G).

What was **not** established: AT-01 to AT-04b at full scale (phases B to D did not run), so the v1.2.2 C2 and C3
criteria were never applied to real full-size data.

## 4. Classification

| Kind | Finding |
|---|---|
| Protocol | Worked as declared: the failure stopped the pilot at the gate. The AT-06b design in v1.2.2 C4 was unable to measure what it was meant to on this fabric (section 5). |
| Implementation | No defect found: the code of record ran (fingerprint), motion reproduced bit for bit, the synthetic direction tests pass. |
| Scientific | No result about the research question. The alignment hypothesis was never tested. |

## 5. Why AT-06b failed (explanation after the fact; not a basis for any change)

- On the 200 pairs, the previous frame without any shift matches the current frame better than either warped
  version: median MSE ratio to the zero-shift MSE is 1.34 for the measured shift U and 1.41 for -U. The zero-shift
  MSE is the smallest of the three in most pairs (U beats it in 16 pairs, -U in 32).
- The S164 fabric moves about 86 px per frame, close to one repeat of its pattern (about 85 px, noted in the run 1
  diagnosis for T1_S164_I199_1). Consecutive frames therefore look almost unchanged, and shifting by +U or -U (about
  one repeat either way) is nearly equally wrong. The test cannot see the direction; 112 of 200 is close to chance,
  with long streaks of either outcome.
- I192 and I193 are the same fabric (S164) at the same speed as I199. Amendment v1.2.2 replaced the validation
  scenario because its motion was noisy, but the underlying limit was the pattern period. Neither the v1.2.2 draft nor
  its audit checked the fabric period against the displacement. That omission is the cause of this failure.
- The measured direction is not reversed: U beats -U in 112 pairs and its median MSE is lower; the sign tests on
  synthetic textures pass.

## 6. What remains true and available

- Stage 1 (v1.2.2) passed (DL-0022); the code base, frozen configuration and full decision record are intact.
- Every test scenario remains unseen at the level of labels, maps, scores and metrics. The raw phase-correlation
  traces of all 13 pilot scenarios have been seen and analysed (DL-0015, DL-0016) and must be disclosed by any later
  study on this dataset.
- Any further work on the alignment question is a new study with its own preregistration. It cannot reuse this
  pilot's gates as if they had passed.
