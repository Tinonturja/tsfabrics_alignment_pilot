# Stage 2 implementation audit

Date: 2026-10-05. Base: Stage 1 record (DL-0012, commit `ebe198c`, PASS 53/53) plus the docs commits after it.
No code was written for this audit, no image was opened, and no GPU was used.

Documents cross-referenced: `PREREGISTRATION.md` (v1.2, sha `182df443...`), `PREREGISTRATION_AMENDMENT_v1.2.1.md`
(sha `4118fc4b...`), `configs/pilot_v1_2_1.yaml`, `docs/decisions/DECISION_LOG.md`, `docs/UNRESOLVED.md`, every module
in `src/tsfpilot/`, the Stage 1 tests, `reference/`, the frozen CSVs, Research Gate v1.1 (superseded, read only to
trace where v1.2 inherits a term), the 2026-09-24 pre-implementation audit, the v1.1 final adversarial audit, and the
official `amazon-science/patchcore-inspection` code checked out at `fcaa92f124fb1ad74a7acf56726decd4b27cbcad`.

## 0. What Stage 2 is, in plain words

Stage 1 proved the arithmetic: windows, variants, events, metrics, chance gate, bootstrap and decision machine, all on
synthetic data. Stage 2 builds the detector and calibrates everything that needs real images, using only frames the
protocol allows: the 300 bank frames per fold, the 1,212 validation frames of `T1_S164_I199_1`, and motion
estimation (no detector) on training-side scenarios. At the end of Stage 2 every number that Stage 3 needs is fixed
and hashed: six coresets (2 folds x 3 seeds), the per-seed validation constants, and tau_r per fold. Stage 3 then
scores test frames once, with nothing left to choose.

## A. Stage 2 implementation map

"S2 GPU" means the acceptance test runs on Kaggle with a GPU. "CPU unit" means an ordinary pytest test that runs
anywhere without data, written before the Kaggle run so that most bugs are caught on synthetic inputs.

| # | Requirement | Frozen source | Planned file / module | Test | Data allowed |
|---|---|---|---|---|---|
| 1 | Only allowed frames can be read; purpose-tagged access | §5 rules 1 to 3; §24 Stage 2 "Data allowed" and "Forbidden" | `src/tsfpilot/access.py` (new) | `tests/test_stage2_access.py` (CPU unit) | Rules only |
| 2 | Bank frame list is the Stage 1 record, not a recomputation | §4; DL-0012 (bank CSV sha `534535eb...`) | `access.py` loads `audit/stage1_kaggle/bank_frames_v1_2_1.csv` and checks the hash | same | Bank CSV |
| 3 | Validation set = I199 frames 1 to 1,212; never a bank or test scenario | §4 validation table; §5 rule 5 | `access.py` structural asserts against the config and clusters CSV | same | Config, CSVs |
| 4 | Decoding `cv2.imread(..., IMREAD_GRAYSCALE)` to uint8 (640, 800) | §6 Decoding (D2) | `frames.read_gray` (Stage 1, unchanged) | AT-01 | Bank, validation |
| 5 | Input tensor: /255, gray to 3 channels, ImageNet mean and std, no resize or crop | §6 Input (D1, D2) | `src/tsfpilot/detector.py` (new) | CPU unit; AT-01 | Bank, validation |
| 6 | Backbone `wide_resnet50_2`, `IMAGENET1K_V1`, eval, no gradients; hooks on layer2 and layer3 | §6 Backbone, Layers | `detector.py` | AT-01 shapes; AT-04b (train-mode BatchNorm would break batch independence) | Validation |
| 7 | Unfold 3 x 3, stride 1, padding 1; flatten order (c, ki, kj) | §6 Patches | `detector.py` | AT-02 against the official `PatchCore._embed`; CPU unit with random weights | Validation frames 1 to 5 |
| 8 | MeanMapper per layer to 1024; layer3 MeanMapper on 40 x 50 then bilinear (align_corners False) to 80 x 100 (D4) | §6 Per-layer projection, Layer-3 alignment | `detector.py` | AT-02 (rel <= 1e-5) | Validation frames 1 to 5 |
| 9 | Aggregator 2048 to 1024; layout (8000, 1024), index 100 r + c | §6 Aggregation, Layout | `detector.py` | AT-01; AT-02 | Validation |
| 10 | Batch 4 frames | §6 Batch; §29 "last partial batch" | `detector.py` | AT-04b | Validation frames 1 to 10 |
| 11 | Bank features in frozen input order: groups ascending, scenarios lexicographic, frames ascending, cells row-major | §6 Coreset row | `src/tsfpilot/coreset.py` (new) | CPU unit on the order function | Bank frames only |
| 12 | Official `ApproximateGreedyCoresetSampler(0.01, 10, 128)`, 24,000 vectors | §6 Coreset | `third_party/patchcore/sampler.py` (official file, unmodified) + `coreset.py` | CPU unit: sampler output size; pin test | Bank features |
| 13 | D5: `_reduce_features` replaced by a row-chunked projection (100,000 rows, same `Linear` weights), on CUDA | §6 Coreset (D5) | `coreset.py` subclass overriding only `_reduce_features` | CPU unit: chunked indices equal unchunked official indices on synthetic features | Bank features |
| 14 | Seeding immediately before the sampler: `random`, `np.random`, `torch.manual_seed`, `torch.cuda.manual_seed_all`; cuDNN deterministic, benchmark off, TF32 off | §6 Seeding | `coreset.py`, `detector.py` | CPU unit (same seed gives same indices); flags written into the report and asserted | n/a |
| 15 | Coresets for seeds 0, 1, 2 per fold, saved (indices and vectors) and hashed; Stage 3 never rebuilds | §6 Coreset seeds; §24 Frozen | `coreset.py`, `scripts/run_stage2.py` | Hash recorded; engineering check: seed 0 rebuilt twice gives identical indices | Bank features |
| 16 | Squared L2, exact 1-NN, `max(0, ||q||^2 + ||b||^2 - 2 q.b)` in fp32, query chunks of 2,000 | §6 Distance (D6) | `src/tsfpilot/scoring.py` (new) | AT-03; CPU unit vs float64 | Validation |
| 17 | Patch score a_t = min distance; frame score s_t = max; raw (80, 100) float32 map, no upsampling, no blur | §6 Patch score, Frame score, Map (D3) | `scoring.py` | AT-01 map shape | Validation |
| 18 | Validation maps per fold and seed (6 x 1,212 maps) | §8 Per-seed constants; §24 Computed | `run_stage2.py` | AT-04a (bit-identical rerun) | Validation |
| 19 | mu0 = mean of a_t over all cells of all validation frames, per fold and seed | §9 Common definitions; §8 | `src/tsfpilot/validation.py` (new) | CPU unit | Validation maps |
| 20 | b1, b3 (3 x 3 max clipped at borders) per fold and seed | §16 Definitions | `validation.py`, reusing `decomposition.m3` | CPU unit | Validation maps |
| 21 | **tau_cell** | Listed in §8, §24, AT-04c, §27 item 7. **Not defined in v1.2** (see section F, item F1) | `validation.py` once the definition is approved | CPU unit | Validation maps |
| 22 | **Deployment thresholds** per variant | Listed in §24; S9 "validation threshold at FA_env <= 2". Full rule only in v1.1 A10 (see F2) | `validation.py`, reusing `events.count_curve` and `variants.scenario_variants` | CPU unit against the direct event definition | Validation maps and validation motion |
| 23 | b1 left-right profile (column means of b1) | §10 C-REV limitation | `validation.py` | trivial | Validation maps |
| 24 | Raw motion (dx, dy, r) on every training-side scenario, full length | §4 "tau_r source"; §7 items 1 and 2; §24 Data allowed | `motion.raw_scenario` (Stage 1, unchanged) driven by `src/tsfpilot/stage2_motion.py` (new) | AT-05 (Stage 1); CPU unit for the scenario selection | Training-side scenarios, motion only |
| 25 | tau_r per fold on the 0.01 grid | §7 item 3 | `motion.tau_r` (Stage 1, unchanged) | CPU unit: scenario lists per fold; never the fold's own test group | Same |
| 26 | Count of constant-crop frames on training-side scenarios | `docs/UNRESOLVED.md` U-I1 | `stage2_motion.py` | Reported count | Same |
| 27 | AT-01, AT-02, AT-03, AT-04a, AT-04b | §23 | `src/tsfpilot/acceptance2.py` (new), run by `run_stage2.py` | Each writes a JSON record | Validation frames |
| 28 | AT-06b warp direction on real frames | §23 AT-06b | `acceptance2.py` | CPU unit on a synthetic moving texture (must pass) and its reversal (must fail) | Validation I199 images and motion |
| 29 | Pinned official code | §6 "pinned to commit fcaa92f"; §25 `third_party/patchcore/` | `third_party/patchcore/` (see F6) | `tests/test_third_party_pin.py`: git blob ids equal those of `fcaa92f` | n/a |
| 30 | Frozen outputs: config hash, coresets, constants per seed, tau_r per fold, environment, git commit | §24 "Frozen at the end of Stage 2" | `run_stage2.py`, `manifest.py` (extended) | Manifest self-check | n/a |
| 31 | Provenance: commit, tree, Python, torch, torchvision, numpy, CUDA, cuDNN, GPU, weights file hash, config, preregistration and amendment hashes, source hashes, notebook hash, coreset hashes, validation-output hashes, seeds, frame-list hash | §25 manifest; user's provenance list | `manifest.py`, `run_stage2.py` | Report schema test | n/a |
| 32 | Kaggle GPU notebook | §24 | `notebooks/stage2_kaggle.ipynb` | Dry run in the sandbox without data | n/a |
| 33 | `requirements.lock` written from the Kaggle environment at the freeze | `requirements.txt` comment (Stage 1) | `run_stage2.py` | Present in the record | n/a |

## B. Stage 2 dependency map

```text
                    FROZEN INPUTS (hash-checked before anything runs)
   PREREGISTRATION.md  amendment v1.2.1  pilot_v1_2_1.yaml  clusters CSV  Stage 1 bank CSV (534535eb...)
            |                                   |                 |                     |
            v                                   v                 v                     v
   +------------------------------- access.py: allow-lists per purpose ----------------------------+
   |  purpose "bank"       : exactly the 300 (scenario, frame) pairs per fold from the bank CSV     |
   |  purpose "validation" : T1_S164_I199_1 frames 1..1212                                           |
   |  purpose "motion"     : full scenarios of the fold's tau_r groups (from the clusters CSV)       |
   +---------------+-----------------------------+-----------------------------------+--------------+
                   |                             |                                   |
         bank frames (uint8)            validation frames (uint8)          motion frames (uint8)
                   |                             |                                   |
                   v                             v                                   v
     detector.py: input tensor -> WRN-50-2 -> layer2 (512x80x100), layer3 (1024x40x50)   motion.raw_scenario
                   -> unfold 3x3 -> MeanMapper -> [layer3: bilinear 40x50 -> 80x100]      (dx, dy, r) per pair
                   -> stack -> Aggregator -> features (8000 x 1024) per frame                      |
                   |                             |                                                |
                   v                             |                                                v
     bank features (2.4M x 1024 per fold,        |                                   motion.tau_r per fold
     disk memmap, never scored)                  |                                      (0.01 grid)
                   |                             |                                                |
                   v                             |                                                |
     coreset.py: seed s -> official sampler      |                                                |
     (chunked projection) -> 24,000 indices      |                                                |
     -> coreset vectors (fold, s), hashed        |                                                |
                   |                             |                                                |
                   +--------------> scoring.py: squared L2 1-NN, fp32 <---------------------------+
                                   validation maps (fold, s): 1212 x 80 x 100                     |
                                                 |                                                |
              +----------------------------------+--------------------------+                     |
              v                                  v                          v                     v
   AT-01 shapes, AT-02 D4 order,       validation.py: mu0, b1, b3,     variants on validation <-- statuses on I199
   AT-03 distances, AT-04a/04b         tau_cell*, b1 profile           (needs mu0, tau_r)          |
                                                                            |                     v
                                                                  deployment thresholds*      AT-06b (images,
                                                                                               U(t,1), per fold)
              \__________________________________ all results ______________________________/
                                                 v
                         stage2_report.json + frozen/ (hashes of every output) + requirements.lock
   * definition pending (section F)
```

Order constraints that matter: tau_r must exist before the validation statuses, so before AT-06b and the deployment
thresholds; mu0 must exist before any V4-family variant is computed on validation maps; the coreset of (fold, seed)
must exist before its validation maps. Validation features do not depend on the fold, so one pass over the 1,212
frames scores all six coresets.

## C. Leakage audit

Every path by which test-scenario information could reach a Stage 2 output, and what stops it. "Structural" means
the code refuses; "procedural" means it depends on the researcher.

| # | Entry point | What could leak | Prevention | How it is tested |
|---|---|---|---|---|
| L1 | Reading any image | A frame of a test scenario scored or inspected | Every Stage 2 image read goes through `access.py`, which accepts a request only if (scenario, frame, purpose) is in that purpose's allow-list. Anything else raises `ForbiddenFrame`. Structural | Unit tests: a test-scenario frame not in the bank CSV, requested as bank, validation or for scoring, raises. A static test fails if any module other than `access.py` calls `frames.read_gray` or `cv2.imread` |
| L2 | Scoring | A bank frame from the other fold's test scenarios is scored (forbidden by §24) | `scoring.py` accepts only feature batches tagged `validation`. Bank features have no code path to a scoring call. Structural | Unit test: passing a `bank` batch to the scorer raises |
| L3 | Labels | Test-scenario labels shape a constant | Stage 2 loads no label file except `T1_S164_I199_1` (to confirm 0 defect frames and to define the validation normal set). The bank comes from the Stage 1 record, so bank eligibility is not recomputed. Structural (label loader allow-list) | Unit test: loading labels for any other scenario through the Stage 2 loader raises |
| L4 | Bank features | Summaries or displays of features drawn from test scenarios (§24: "never scored, displayed or summarised") | Bank features live in a temporary memmap, are deleted after the coresets are built, and are never written to the record. The report records only shapes, counts and hashes. Coreset indices are saved (required by §6) but no per-scenario breakdown of coreset membership is printed | Report schema test: no numeric statistic of bank features |
| L5 | Validation scenario | Validation overlaps a bank or a test set | Asserts at start-up: I199 is not in either fold's test list or bank quotas with a quota above 0, and its group is not either fold's test group. Structural | Unit test against the config |
| L6 | tau_r | A fold's own test scenarios enter its tau_r | Scenario lists come from the clusters CSV filtered by `tau_r_groups`; an assert rejects any scenario of the fold's own test group. tau_r uses phase correlation only, never detector output | Unit test: lists equal the §4 text (A-G1: G2, G3, G4; A-G4: G1, G2, G3 including T1_S177_I108_1) |
| L7 | Motion on the other fold's test scenarios | Allowed by §24 for tau_r. Risk: those per-frame motion arrays later tempt someone to look at test-scenario behaviour | They are label-free and identical to what Stage 3 recomputes. They are stored only as inputs to tau_r, never joined with labels, passes or scores. Procedural beyond that | Report contains per-scenario pair counts and the constant-crop count only |
| L8 | Deployment thresholds | Computed on test data | Computed on validation maps and validation motion only; the function takes no test layout | Unit test signature; values recorded per fold and seed |
| L9 | Coreset of the other fold | A-G1's coreset holds features of A-G4 test frames, and vice versa | This is by design (§24, defect 1 of §31): training-side for that fold. Never used to score the frames it came from | L2 guard |
| L10 | Kaggle notebook | Ad hoc cells that open or plot forbidden frames | The notebook only calls `run_stage2.py`; the runner logs which (scenario, purpose) pairs were read and the final report asserts the read log is a subset of the allow-lists. Procedural plus an audit trail | Read-log check inside the runner |
| L11 | Stage 3 artefacts appearing early | Any map of a test scenario | No Stage 3 code is written in Stage 2. The Stage 2 runner has no test-scenario scoring path at all | Code review; L1 and L2 tests |

Residual: blinding is procedural (§27 item 9). One person runs Kaggle and the full dataset is attached. The guards
make a breach deliberate and visible in the read log, not impossible.

## D. Risk register

| # | Risk | Impact | Likelihood | Detection | Response (never weaken a test) |
|---|---|---|---|---|---|
| R1 | No run of 200 consecutive reliable pairs exists in I199. The forensic table (label-free motion statistics, already part of the frozen record) gives I199 a dx IQR of 200 px and a median phase-correlation response of 0.50, against 4 to 5 px and 0.74 for I192 and I193 | AT-06b cannot be executed as worded | Medium to high | The runner reports the longest reliable run per fold | Needs a pre-declared rule now (F3) |
| R2 | AT-04b (batch 1 vs 4, rel <= 1e-6) fails because cuDNN picks different convolution algorithms per batch size, and the fp32 expansion `||q||^2 + ||b||^2 - 2 q.b` amplifies small feature differences | Stage 3 blocked | Medium | AT-04b reports rel at feature level and at map level separately, so the cause is visible | Diagnose. If the code is right and the hardware cannot meet 1e-6, that is a specification problem to report, not a tolerance to loosen |
| R3 | Feature layout bug: wrong flatten order, wrong hook, layer3 grid mismatch, train-mode BatchNorm | Wrong detector | Medium before tests | AT-02 compares against the official `_embed`; a CPU test does the same with random weights on small inputs | Fix code |
| R4 | Coreset not reproducible: input order, RNG consumption order, nondeterministic CUDA kernels | Hidden extra seed | Low to medium | Engineering check: seed 0 built twice gives identical indices; CPU test that the chunked projection gives the same indices as the official unchunked one | Fix code |
| R5 | Plain instead of squared distance, fp16 or TF32 | Wrong scores | Low | AT-03 against float64 squared distances; TF32 and cuDNN flags asserted and recorded | Fix code |
| R6 | Kaggle memory and disk: 9.8 GB of fp32 bank features per fold; a T4 or P100 has 16 GB | Crash | Medium | Pre-flight check of free disk, RAM and GPU memory | Disk memmap, one fold at a time, chunked projection (D5, frozen) |
| R7 | tau_r undefined for a fold | Fold is motion-invalid (C0c, outcome path M); AT-06b has no reliable pairs for it | Low | Reported in Stage 2 | Legitimate scientific result, recorded before any test score exists. AT-06b handling needs a pre-declared rule (F3) |
| R8 | Official code cannot be imported (its `common.py` imports `faiss` at import time; `backbones.py` imports `timm`) | AT-02 reference unavailable | Medium | Import check in the pre-flight | Install pinned `faiss-cpu`; record `timm` (F6) |
| R9 | Weights or library versions differ between Stage 2 and Stage 3 (another GPU type, a new Kaggle image) | AT-04c fails at the start of Stage 3 | Medium | AT-04c | The frozen path: repeat Stage 2 on the Stage 3 hardware. Advice: pick one accelerator type now and keep it for both stages |
| R10 | numpy 2.4.4 (required by AT-15) incompatible with the Kaggle torch build | Import failure | Low to medium | Pre-flight import check | Isolated install as in Stage 1; record versions |
| R11 | GPU budget for Stage 3 (estimate: about 8 x 10^16 FLOP for 68,660 test frames x 3 coresets, roughly 4 to 5 hours on a T4) | Session limits | Medium | Timing of Stage 2 phases gives a measured rate | Not a Stage 2 issue; the measured rate goes into the Stage 3 plan |
| R12 | Validation maps or constants drift because of accumulation order | AT-04c noise | Low | Constants accumulated in float64; summation order fixed and documented | n/a |

## E. Implementation order

Each step ends with CPU tests that run in the sandbox and on Kaggle without a GPU. Nothing touches the dataset until
step 8.

1. **Decisions recorded.** The answers to section F go into `docs/decisions/DECISION_LOG.md` as DL-0013 before any
   code that depends on them.
2. **Pinned official code.** `third_party/patchcore/` at `fcaa92f` plus `tests/test_third_party_pin.py`.
3. **Access gate.** `access.py` with the three allow-lists, the label allow-list, the read log and the start-up
   asserts; `tests/test_stage2_access.py`, including the static test that nothing else reads images.
4. **Feature path.** `detector.py`; CPU test against the official `_embed` with a randomly initialised WRN-50-2 on
   a small input, plus the layer-by-layer shape trace at 640 x 800.
5. **Coreset.** `coreset.py` (input order, seeding, chunked projection subclass, save and hash); CPU tests on
   synthetic features.
6. **Scoring.** `scoring.py`; CPU test against float64 brute force, and the guard that refuses bank batches.
7. **Motion, tau_r, validation constants, deployment thresholds, AT-06b.** `stage2_motion.py`, `validation.py`,
   `acceptance2.py`; CPU tests on synthetic maps and a synthetic moving texture.
8. **Runner and notebook.** `scripts/run_stage2.py` in resumable phases, `notebooks/stage2_kaggle.ipynb`, report
   and freeze manifest. Dry run without data in the sandbox.
9. **Kaggle, in this order, stopping at the first failure:**
   - Phase A (CPU): motion on training-side scenarios, tau_r per fold, AT-06b.
   - Phase B (GPU, smoke): AT-01 and AT-02 on validation frames 1 to 5. If either fails, stop before any bank feature
     is computed.
   - Phase C (GPU): bank features per fold, coresets for seeds 0, 1, 2, hashes, reproducibility check of seed 0.
   - Phase D (GPU): validation maps for all six coresets in one pass; AT-03, AT-04a, AT-04b.
   - Phase E (CPU): mu0, b1, b3, tau_cell, b1 profile, deployment thresholds; freeze manifest; report.
10. **Record.** The Stage 2 outputs are committed as the record (hashes and small files in git; the coreset vectors
    and validation maps as a Kaggle dataset version whose file hashes are in git), DL-0014 written, U-I1 updated.

Commits, in this order: (1) decisions and pinned code; (2) access gate; (3) detector; (4) coreset and scoring;
(5) motion driver, validation constants, AT-06b; (6) runner and notebook; (7) the Stage 2 record after Kaggle.

## F. Conflicts and ambiguities that need a decision before code

Nothing below changes a decision quantity of the pilot (C0 to C7, outcomes). Each one is a place where the frozen
text leaves a free choice, and I will not pick a value silently.

**F1. tau_cell is listed but never defined in v1.2.**

- Where it appears: §8 "Per-seed constants" (line 204), §24 Stage 2 "Computed" (line 740), AT-04c (line 706: "relative
  difference <= 1e-4 on mu0 and tau_cell"), §27 item 7 (line 858).
- Where it was defined: v1.1 A12, "tau_cell = the 99.9th percentile of a_t over all cells of all validation frames",
  used there for the global-elevation class g. v1.2 §16 replaced that class with a median-offset test and no longer
  uses tau_cell anywhere.
- Why it matters: AT-04c must check it at the start of Stage 3, so Stage 2 must compute something.
- Smallest safe resolution: compute it with the v1.1 A12 definition (numpy `percentile`, method 'linear', as in §18)
  per fold and seed, record it, and state that it has no role in any v1.2 rule. Logged as a clarification in DL-0013.

**F2. Deployment thresholds have no v1.2 definition beyond "validation threshold at FA_env <= 2" (S9).**

- v1.1 A10: "each variant's threshold = the smallest tau with FA_env <= 2 on validation frames (no passes there),
  then applied to test."
- Smallest safe resolution: for each fold, seed and variant (V0, V1, V2, V4, V4-reverse, V4-lagperm, V4-oracle), apply
  the §14 tau_2 rule to the validation timeline: N_val = I199 frames with label in {1, 2} (all 1,212; the scenario has
  0 defect frames), no pass windows, events by §12 (cap 25), grid T = +infinity plus the distinct validation scores,
  integer test 1000 x Count <= 2 x |N_val|. Variants use the fold's tau_r statuses on I199 and the fold-and-seed mu0.
  Diagnostic only (S9).

**F3. AT-06b: which 200 pairs, which cells, and what if they do not exist.**

- Text (line 709): "200 consecutive reliable validation pairs (T1_S164_I199_1) ... MSE(img_t, W(img_(t-1), U(t,1))) <
  MSE with -U(t,1) on valid cells ... holds for >= 95% of pairs."
- Open points: (a) statuses depend on tau_r, which differs by fold; (b) "consecutive" may have no solution in I199
  (R1); (c) "valid cells" could mean each warp's own valid columns or the columns valid for both.
- Smallest safe resolution, declared now before any I199 motion is computed: run per fold; use the earliest t0 such
  that frames t0 .. t0+199 are all `reliable`; if no such run exists, use the first 200 reliable frames in time order
  (each pair is (t-1, t) with frame t reliable); compare both MSEs on the same cells, those valid for both U and -U;
  a pair counts only if the U-warp MSE is strictly smaller; pass if at least 190 of 200 pairs hold. If a fold's tau_r
  is undefined, AT-06b is not applicable to that fold (its V4 always falls back to V2), and the report says so.

**F4. AT-03: which 2,000 queries.**

- Text (line 703): "2,000 validation queries vs seed-0 coreset".
- Smallest safe resolution: per fold (each fold has its own seed-0 coreset), validation frame 1, cells 0, 4, 8, ...,
  7,996 in row-major order. Deterministic, covers all 80 rows, introduces no new random seed.

**F5. Fixture frames and coresets for AT-01, AT-02, AT-04a, AT-04b.**

- Text names only counts (1, 5, 10, 10 validation frames).
- Proposed default (no decision needed unless you object): AT-01 frame 1; AT-02 frames 1 to 5; AT-04a and AT-04b frames
  1 to 10. AT-04a and AT-04b are run for all six coresets, which is stricter than one.

**F6. The official code: submodule versus pinned copy.**

- §25 (line 791) and the §30 checklist (line 922) say `third_party/patchcore/` is a git submodule at `fcaa92f`. The
  repository has no submodule; Stage 1 did not need it.
- Problem with a submodule here: you apply my work with `git am` and upload the repository to Kaggle as a dataset.
  Neither carries submodule contents unless you also run `git submodule update` with network access.
- Smallest safe resolution: copy the four needed files (`sampler.py`, `common.py`, `patchcore.py`, `backbones.py`) plus
  `LICENSE` and `NOTICE` byte-for-byte from `fcaa92f` into `third_party/patchcore/`, and add a test that recomputes
  each file's git blob id and compares it with the id in the upstream tree at `fcaa92f`. Importing `common.py` needs
  `faiss` and `backbones.py` needs `timm`; both are used only by the AT-02 reference, so `faiss-cpu` is installed
  (pinned) in the Stage 2 notebook and the installed `timm` version is recorded.

**F7. "AT-04" in the Stage 2 request.**

- v1.2 has no standalone AT-04. The family is AT-04a and AT-04b (Stage 2) and AT-04c (start of Stage 3, line 706).
- Resolution: Stage 2 runs AT-04a and AT-04b. The AT-04c function is written in Stage 2 (Stage 3 calls it) but its
  record run belongs to the start of Stage 3, as frozen.

**F8. Naming drift, no decision needed.** §24 and §25 name `configs/pilot_v1_2.yaml`; the repository uses
`configs/pilot_v1_2_1.yaml` since the amendment. The config file is not edited in Stage 2: its hash is recorded in
the Stage 1 report, and Stage 2 constants are outputs written to `frozen/`, not config keys. Acceptance-test
tolerances and fixture sizes stay in the preregistration and in one Stage 2 constants module, with a test that the
numbers match the AT table text.

## G. Decisions (Tinon, 2026-10-05, before any Stage 2 code)

| Item | Decision |
|---|---|
| F1, F2 | Adopt the v1.1 A12 definition of tau_cell and the v1.1 A10 deployment rule, applied with v1.2 machinery as written in F1 and F2. Logged as clarification DL-0013; the v1.2 text is not edited |
| F3 | AT-06b as written in F3: per fold; earliest run of 200 consecutive reliable frames, else the first 200 reliable frames in time order; both MSEs on the cells valid for U and -U; strict inequality; pass at >= 190 of 200; not applicable to a fold with undefined tau_r |
| F4 | AT-03 queries: per fold, validation frame 1, cells 0, 4, ..., 7,996 |
| F5 | Defaults accepted: AT-01 frame 1; AT-02 frames 1 to 5; AT-04a and AT-04b frames 1 to 10 on all six coresets |
| F6 | Byte-for-byte copy of the official files at `fcaa92f` with a git-blob-id test; pinned `faiss-cpu` installed for the AT-02 reference import |
| F7, F8 | As written |
