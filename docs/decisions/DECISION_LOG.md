# Decision log

Each entry says what was decided, when, on what evidence, and whether any TSFabrics test-scenario detector output
existed at the time. Up to and including DL-0020, none did: no anomaly map, score or metric has been computed on any
frame of a test scenario. The only detector outputs computed so far are validation-frame numbers of the Stage 2 smoke
run (DL-0015).

| ID | Date (UTC) | Decision | Evidence | Test outputs seen? |
|---|---|---|---|---|
| DL-0001 | 2026-09-27 | Freeze Research Gate v1.2 (`PREREGISTRATION.md`, SHA-256 `182df443...a70dd`) | Synthetic audits; frozen CSVs | No |
| DL-0002 | 2026-09-30 17:14 | C0b calibration protocol frozen (`calibration/c0b/PROTOCOL.md`, `d537d67c...544be`) | None (written before any trace) | No |
| DL-0003 | 2026-09-30 | Calibration kernel validated: 8 of 8 exact matches with the Fraction reference | Synthetic traces | No |
| DL-0004 | 2026-09-30 ~20:15 | First FAILs (A-G1 N3, N4); `ADDENDUM-1.md` written and hashed (`30ae3d23...4a1`) before any diagnostic or candidate | Partial primary results | No |
| DL-0005 | 2026-09-30 | Primary complete: 6 FAIL, 3 INDETERMINATE. D1 to D4 locate the failure in the restricted offset set | Synthetic only | No |
| DL-0006 | 2026-09-30 | Candidate A1 (uniform offsets) passes 18 of 18 cells; pooled 4.76%; residual 6.2% under a strong periodic null | Synthetic only | No |
| DL-0007 | 2026-10-01 02:30 | **Amendment v1.2.1 adopted** by Tinon (`PREREGISTRATION_AMENDMENT_v1.2.1.md`, `4118fc4b...a1039`) | Calibration report | No |
| DL-0008 | 2026-09-30 | Literature audit: ST-PaveCLIP closest neighbour (class B); controls and combination class D; MAP-VD class E | `docs/literature/` | No |
| DL-0009 | 2026-10-03 | Stage 1 implementation choices where the text is silent (below); Stage 1 suite run in the sandbox: 48 passed, 3 skipped (AT-14 needs the dataset) | `audit/stage1_report_sandbox.json` | No |
| DL-0010 | 2026-10-03 | Independent code audit against the specification: no defect changing a decision quantity found. Two gaps fixed: C0c (motion-invalid) had no function, now `motion.motion_invalid` with a strict integer 5% test; constants written in code are now checked against the YAML by a test | Independent audit notes | No |
| DL-0011 | 2026-10-04 | Pre-Kaggle repository audit. Plumbing fixes only, no methodological change: (1) Kaggle notebook installs the pinned packages into an isolated folder, checks the install and the imported numpy version, and refuses to run if the repository or dataset is ambiguous or missing; (2) `layout.py` (reference and calibration) locates the frozen CSV from its own folder name instead of a path-substring test; (3) the Stage 1 report hashes reference, calibration, scripts and the notebook too, plus one fingerprint over all hashed files; (4) `calibration/c0b/HASHES_NOTE.md` explains the single expected `HASHES.txt` mismatch (`layout.py`) | Fresh clone in a clean environment: 50 passed, 3 skipped (AT-14) | No |
| DL-0012 | 2026-10-04 | **Stage 1 PASS (the record).** Kaggle, CPU, commit `ebe198c` (tree `d266f18b...`): 53 passed, 0 failed, 0 skipped, including the three AT-14 dataset tests. Files fingerprint `a27ac91d1f82e4981576ba771bfe148e09146584fcc6c8a9ca6ed57c88c20e6e` equals the fingerprint of the committed tree. Report SHA-256 `41ca8d47daa5b96cdfba15c963d1b86988c071591af6c98850c4e3c229c9d911`; bank frames CSV `534535eb8ea947bed4fb9c9a03352f52ba0ba197ba7694385b5735e9b936a535`. Python 3.13.15, numpy 2.4.4, numba 0.68.0, OpenCV 4.13.0. Stage 2 may start | `audit/stage1_kaggle/` | No |
| DL-0013 | 2026-10-05 | **Stage 2 implementation audit and clarifications** (`docs/stage2/STAGE2_IMPLEMENTATION_AUDIT.md`, section G). Terms that v1.2 lists but does not define take their v1.1 definitions: tau_cell = 99.9th percentile (numpy 'linear') of a_t over all cells of all validation frames, per fold and seed; deployment threshold = the section 14 tau_2 rule on the validation timeline, per fold, seed and variant. AT-06b, AT-03 and AT fixture choices fixed as in section G. Official PatchCore files copied byte-for-byte from `fcaa92f` (blob ids tested) instead of a submodule. No decision quantity changes | Specification text only; no image, map, score or motion estimate of any scenario computed | No |
| DL-0014 | 2026-10-05 | Stage 2 code written and unit-tested on CPU; implementation choices where the text is silent are listed below. No Kaggle run yet | CPU tests on synthetic data; a CPU smoke run of the runner on synthetic frames with random backbone weights | No |
| DL-0015 | 2026-10-06 | **Stage 2 run 1 FAIL at phase A** (Kaggle notebook version 1, T4, files fingerprint `b918ed8b...`, report `51a270cc...`). A-G1 tau_r 0.00; A-G4 tau_r undefined (best 93.6% consistent at 0.75), so A-G4 is motion-invalid under the frozen rule; AT-06b A-G1 92 of 200. Smoke run (not the record): AT-04b maps rel up to 1.1e-5 against a 1e-6 limit. Diagnosis in `docs/stage2/STAGE2_RUN1_DIAGNOSIS.md`: G1 frame-interval alternation at the edge of the consistency band; I199 aliasing; squared-distance amplification. No code error found | Phase A record, smoke phases B and D, the 13 motion files (hashes match `phase_A.json`) | No |
| DL-0016 | 2026-10-06 22:18 | **Amendment v1.2.2 adopted** by Tinon (`docs/stage2/AMENDMENT_v1.2.2_PROTOCOL.md`, SHA-256 `276fe9838efb6f6e334705b131d16c93f5d3c8d681b23fba57e15bb3fa25a704`). A post-Stage-2 diagnostic amendment, not preregistered: motion candidate M1 with band (b) B(M) = max(8, 0.2 x \|M\| / 2); AT-04b, AT-03 and AT-06b revised. Text written as draft, audited (`AMENDMENT_v1.2.2_AUDIT.md`, blockers B1 to B6, changes D1 to D9), then adopted. Hashed before any calibration or real-data computation under M1. Calibration implementation notes below | Draft, audit, diagnosis; no M1 flag, status or tau_r computed on any data | No |
| DL-0017 | 2026-10-06 22:39 | **M1 synthetic calibration FAIL; M1 not adopted.** 14 of 16 criteria pass (corrected by DL-0019). Failed: criterion 1, F6 item 4 (98.25% clean frames reliable, limit 99%); criterion 3, F4 item 4 (3.01 points below the frozen rule, limit 1). Under v1.2.2 the frozen motion rule stays, A-G4 stays motion-invalid, and no second candidate is tried. Result `calibration/v1_2_2_m1/result.json` (`7a82d069...e6ff`), code `d1c31f4` committed before the run | `calibration/v1_2_2_m1/REPORT.md`; synthetic data only | No |
| DL-0018 | 2026-10-07 | **Protocol fallback taken** (Tinon's choice after DL-0017): v1.2.2 section 5 steps 1 to 4 proceed with the frozen motion rule and the C2 to C4 changes. `configs/pilot_v1_2_2.yaml` (motion.rule frozen, stage2_acceptance section) becomes the default configuration; AT-03 fallback, AT-04b two-part criterion and AT-06b on I192/I193 implemented; Stage 1 and Stage 2 notebooks updated. With A-G4 motion-invalid, any Stage 3 seed-0 outcome can only be B\* (final I), or M or G if A-G1 is also invalid (section 22). Stage 3 is not authorised yet. Implementation notes below | CPU tests; a CPU smoke run of the Stage 2 runner on synthetic frames with random weights (not a record) | No |
| DL-0019 | 2026-10-07 | **Erratum, record only.** DL-0017 and `calibration/v1_2_2_m1/REPORT.md` said "16 of 18 criteria pass" (REPORT: "18 checked, 16 pass"). The record `result.json` (`7a82d069...e6ff`, unchanged) has 16 criteria, of which 14 pass: section 4 defines 6 checks under criterion 1, 4 under criterion 2 and 6 under criterion 3. The two failed criteria, their values, the FAIL verdict and the rejection of M1 are unchanged. DL-0016 and DL-0017 were dated 2026-10-07 (local date); their UTC times, from the commits, are 2026-10-06 22:18 and 22:39. No code, configuration, criterion or result changed | `result.json`; commits `8f23224`, `540e333` | No |
| DL-0020 | 2026-10-07 05:44 | **Stage 1 (v1.2.2) run 1 FAIL.** Kaggle CPU, notebook version `355951562`, repository dataset version 3 (222 files), torch 2.11.0+cpu, Python 3.13.15, numpy 2.4.4. 142 passed, 1 failed, 0 skipped. Files fingerprint `b47f99f1...b1fa` (equals the committed tree), config `c22f6096...`, bank CSV `534535eb...` (equals DL-0012). Report SHA-256 `94a78aa9f51b2ffcc0784b988cca3a781db917d026fd2da5410d4c807b68fded`; files in `audit/stage1_kaggle_v1_2_2_run1_FAIL/`. Failed test: `test_stage2_scoring::test_chunking_does_not_change_results`, which required bit-identical float32 distances for chunk sizes 50 and 333. Classification: implementation defect in a unit test written for DL-0014, not a protocol or scientific result. The math library may choose a different kernel for a different matrix shape; the difference is one float32 rounding step (reproduced in the sandbox with MKL restricted to AVX2: 1 of 333 values, relative 1.3e-7). The scorer is unchanged and the pipeline always uses chunks of 2,000 aligned to the 8,000 cells of a frame. Tinon approved replacing the test (DL-0021) and a new Stage 1 run; this failed run stays on record | Kaggle record above; sandbox reproduction | No |

## DL-0009: implementation choices (none changes a frozen rule)

| # | Where | Choice | Why it is allowed | Can it change a result? |
|---|---|---|---|---|
| I-1 | Section 7 item 5 | A frame without a phase-correlation estimate (std < 1e-6, or right after such a frame) follows the v1.2 status text: `held` if within 5 frames of the last reliable estimate, else `unknown`. v1.1 pseudo-code E2 marked such frames `unknown` | v1.2 text governs; logged in `docs/UNRESOLVED.md` U-I1 | No for the pilot: no test scenario has a constant crop |
| I-2 | Section 7 item 6 | The sum u_(t-i+1) + ... + u_t is accumulated sequentially in ascending j in float64 | Fixes the floating-point order the text leaves open | Only if a sum lands within ~1e-15 of a .5 boundary |
| I-3 | Section 18 | Draws are `rng.integers(0, n, n)` per unit type, converted to multiplicities | The text fixes the generator and the order, not the call | No (any fixed call is a valid draw) |
| I-4 | Section 18 | Units are numbered in sorted (scenario, bin) order | Makes unit indices independent of discovery order | No |
| I-5 | Section 18 | Replicates are computed for all seven variants, not only those in CIs | "every variant" | No |
| I-6 | Section 18 | Integer products in the bootstrap use float64 BLAS with an exactness guard (< 2^52) | Speed; exact for these magnitudes | No |
| I-7 | AT-17 | "+/- 10%" read as +/- 10 percentage points of each tabulated class share | The table gives shares as counts over events | AT-17 only; non-blocking |
| I-8 | AT-15 | Added a regression test: the pipeline's k equals the calibration kernel's k on all 200 traces of the amendment's fixture cell, and 6 of 200 are not collapsed | Ties the pipeline to the calibration evidence | No |
| I-9 | `reference/layout.py`, `calibration/c0b/layout.py` | The absolute CSV path was replaced by a repository-relative path | Portability; logic unchanged | No |
| I-10 | Tests only | Stage 1 builds the fold layouts from the passes CSV with synthetic labels (label 4 inside each pass, 1 elsewhere) and scenario-median k | Gives the same N_f as the real labels; AT-14 checks the assumption on the real label files | No (tests only) |

## DL-0014: Stage 2 implementation choices (none changes a frozen rule)

| # | Where | Choice | Why it is allowed | Can it change a result? |
|---|---|---|---|---|
| S2-1 | Section 6, Layers | layer2 and layer3 are read by calling the torchvision modules in order up to layer3, not with forward hooks | The same computation; AT-02 compares the output with the hooked official `_embed` | No |
| S2-2 | Section 6, Coreset | The official `run()` is called unchanged; a subclass overrides only `_reduce_features` (D5) and records the indices the sampler returns | Indices must be saved (section 6) and `run()` returns only vectors | No |
| S2-3 | Section 24 | Validation features do not depend on the fold, so one pass over the 1,212 frames scores all six coresets | Same maps as six separate passes | No |
| S2-4 | Section 24 | Bank features live in a temporary disk array and are deleted once the fold's coresets exist | "Never scored, displayed or summarised" | No |
| S2-5 | Section 6, Distance | Expression order `(sum q^2) + (sum b^2) - 2 q.b`, clamp at 0, then the minimum | The text fixes the formula, not the floating-point order; AT-03 bounds the error | Only at the rounding level AT-03 measures |
| S2-6 | Section 9 | mu0 accumulated in float64 over the float32 maps | Fixes the summation precision | No |
| S2-7 | AT-02 | One frame at a time for both paths | Isolates the D4 order from batch effects (AT-04b tests batches) | No |
| S2-8 | AT-03 | faiss `IndexFlatL2` distances are also recorded, not gated | Shows the official tool has the same float32 behaviour | No |
| S2-9 | Stage 2 runner | Stops at the first failed phase; `--smoke` caps sizes and is never the record | No result is produced after a failed acceptance test | No |
| S2-10 | Section 7 | Raw motion is computed once per scenario and shared by both folds; each fold's tau_r uses only its own list | Raw estimates do not depend on the fold | No |
| S2-11 | U-I1 | Reported count: frames after frame 1 without an estimate (constant crop or right after one) | Uses Stage 1 functions unchanged | No |

## DL-0016: calibration implementation notes (approved with the adoption)

| # | Where | Choice | Why it is allowed | Can it change a result? |
|---|---|---|---|---|
| V-1 | v1.2.2 section 4, frozen rule | `motion.tau_r` returns only tau, not per-pair flags. `motion.frozen_consistency_flags` runs the same loop and calls the frozen `_consistent`; a test shows that the tau from these flags, with the frozen grid rule, equals `motion.tau_r` on random inputs. `motion.tau_r` and `motion.statuses` are unchanged | Section 4 needs the item 3 flag per frame; the test ties it to the frozen function | No |
| V-2 | v1.2.2 section 4, sets | "Frames 2 to 20 are warm-up and excluded for both rules" applies to every set, including event frames | The sentence is not limited to clean frames | Only which frames are counted |

## DL-0018: v1.2.2 implementation notes (none changes a rule of the adopted text)

| # | Where | Choice | Why it is allowed | Can it change a result? |
|---|---|---|---|---|
| V-3 | C3 (AT-03) | The fallback bound is computed and recorded for every run, also when the primary criterion passes; it decides only when the primary fails | "Both results are recorded" | No |
| V-4 | C3 (AT-03) | b* is found with an explicit first-index search over the float64 distances (torch's `min` does not promise the first index on ties) | The text fixes "smallest-index" | No |
| V-5 | C2 (AT-04b) | The batch-4 maps are the AT-04a maps (same batch composition, AT-04a requires them bit-identical across runs); features are extracted again in both batchings | Same values as a fresh batch-4 pass | No |
| V-6 | C4 (AT-06b) | Selection file `motion/at06b_selection_<fold>.json` holds the rule, the pairs with U and the SHA-256 of each scenario's status array; its own hash is in the phase A record. Images are fetched through `FrameGate.motion_image`, which returns a bare array (never a detector batch) | "Written to the record with its hash before any image is read" | No |
| V-7 | C4 (AT-06b) | The zero-shift MSE (reported, not gated) uses the same columns as the U / -U comparison | Comparable numbers | No (not gated) |
| V-8 | Section 5 step 3 | The Stage 1 suite now contains the Stage 2 CPU tests, so the Stage 1 notebook also installs `requirements-stage2.txt` (faiss); a skipped test would make Stage 1 FAIL | Unchanged pass rule | No |
| V-9 | Section 5 step 1 | `pilot_v1_2_1.yaml` still loads under its own schema (the DL-0012 record stays reproducible). The M1 calibration of DL-0017 ran before `pilot_v1_2_2.yaml` existed, so `result.json` records the v1.2.1 config hash; the motion constants it used are identical in both files (tested) | Record of what was run | No |
| V-10 | Stage 2 runner | Preconditions now also require: the v1.2.2 config and amendment hash, a pinned v1.2.2 Stage 1 record made with the same config, and its bank CSV equal to the DL-0012 bank | Section 5 steps 3 and 4 | No |

## Note on commit identifiers

On 2026-10-03, before the first push, the local history was rewritten to remove commit-message trailers and one private detail from the literature notes. Commit `e42998c` named in `audit/stage1_report_sandbox.json` is the pre-rewrite identifier of `d3466f6` (same code). The sandbox report is not the Stage 1 record; the Kaggle run is.
