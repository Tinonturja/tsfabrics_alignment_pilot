# Stage 2 walkthrough: what each piece does and how to check it yourself

This is the reading guide for the Stage 2 code. For every component: what it does, why the pilot needs it, the
idea behind it, its input and output, what can go wrong, and how it is tested. The section numbers refer to
`PREREGISTRATION.md`; DL-0013 is the decision log entry that fixed the open choices.

Read the files in this order: `access.py`, `detector.py`, `coreset.py`, `scoring.py`, `stage2_motion.py`,
`validation.py`, `acceptance2.py`, then `scripts/run_stage2.py`.

## 1. The access gate (`src/tsfpilot/access.py`)

**What it does.** Every image Stage 2 opens is requested through `FrameGate` with a purpose: `bank`, `validation`
or `motion`. The gate checks the request against an allow-list and raises `ForbiddenFrame` otherwise. Decoded
pixels travel inside a `FrameBatch` that remembers its purpose, so the scorer can refuse anything that is not a
validation frame.

**Why.** Section 24 allows three kinds of data in Stage 2 and forbids scoring any frame of a test scenario. A
comment saying "do not do this" is not protection; an exception is. The full dataset is attached on Kaggle, so
without a gate nothing stops a convenience cell from scoring a test frame.

**Idea.** Least privilege: code can only reach data it is entitled to. The allow-lists come from frozen sources: the
Stage 1 bank record (hash-checked), the config's validation range, and the clusters CSV for the tau_r scenarios.

**Input / output.** Dataset root, config, bank record. Output: decoded uint8 frames, plus a read log that ends up in
the Stage 2 report.

**What can go wrong.** A second code path that reads images without the gate. A bank list that silently differs from
the Stage 1 record. A tau_r list that includes the fold's own test group.

**Tests.** `tests/test_stage2_access.py`: the tau_r lists equal the section 4 text; a changed bank file is refused;
bank frames are only valid for their own fold; test-scenario frames outside the bank are refused for every
purpose; motion frames cannot feed the detector; labels are readable only for the validation scenario; and a
static test fails if any module other than `frames.py` and `access.py` calls the image decoder.

## 2. The feature path (`src/tsfpilot/detector.py`)

**What it does.** Turns a gray 640 x 800 frame into 8,000 feature vectors of 1,024 numbers, one per 8 x 8 pixel cell.

**Why.** PatchCore never trains a network. It describes every small region with features from a pretrained CNN and
asks how far each description is from anything seen in normal frames. The quality of that description is the
detector.

**Idea, step by step.**

1. Normalise like ImageNet: divide by 255, copy the gray channel three times, subtract the ImageNet mean and divide
   by the standard deviation. No resize (D1): resizing to 224 px would shrink an 8 px defect to about 2 px.
2. Run WideResNet-50-2 up to `layer3`. `layer2` has stride 8 (80 x 100 cells, 512 channels, fine texture);
   `layer3` has stride 16 (40 x 50 cells, 1,024 channels, more context).
3. Give each cell its 3 x 3 neighbourhood (`F.unfold`), so a cell "sees" its surroundings. The vector is ordered
   channel first, then the 3 x 3 positions.
4. Shrink each layer's vector to 1,024 numbers with adaptive average pooling (the official "MeanMapper").
5. Bring `layer3` to the 80 x 100 grid with bilinear interpolation. The official code interpolates before step 4;
   we pool first (D4). Both are linear maps on different axes, so the order does not change the result beyond
   rounding, and it saves memory.
6. Stack the two 1,024-vectors and pool 2,048 numbers down to 1,024 (the official "Aggregator").

**Input / output.** (B, 640, 800) uint8 to (B, 8000, 1024) float32. Cell index = 100 x row + column.

**What can go wrong.** Train-mode BatchNorm (results depend on the batch); a wrong flatten order before pooling
(numbers look plausible but differ from PatchCore); a wrong layer; layer3 not aligned to the layer2 grid.

**Tests.** `tests/test_stage2_detector.py` runs the official `PatchCore._embed` from the pinned code on the same
input, with random weights on a small image, and requires the same features (rel <= 1e-5). It also checks the unfold
order against the official `PatchMaker`, the hooked layer outputs, batch independence and the input tensor. On
Kaggle, AT-01 checks the full-size shapes and AT-02 repeats the official comparison on real validation frames with
the real weights.

**Try it.**

```python
import numpy as np, torch
from tsfpilot import config, detector as D
cfg = config.load()["detector"]
net = D.load_backbone("cpu", pretrained=False)        # random weights; no download
trace, l2, l3, f = D.shape_trace(net, np.zeros((640, 800), np.uint8), cfg, "cpu")
for name, shape in trace:
    print(f"{name:15s} {shape}")
```

## 3. Coresets (`src/tsfpilot/coreset.py`)

**What it does.** Per fold, writes the features of the 300 bank frames (2.4 million vectors, about 9.8 GB) to a
disk array, then picks 24,000 of them (1%) with the official approximate greedy coreset sampler, for seeds 0, 1
and 2. Indices and vectors are saved with SHA-256 hashes. The bank features are deleted afterwards.

**Why.** Comparing every validation or test cell with 2.4 million vectors is too slow. A random 1% would lose rare
normal patterns, and a missing normal pattern becomes a false alarm. The greedy sampler keeps the set spread out.

**Idea.** Greedy k-center: start from 10 random points, then repeatedly add the vector farthest from everything
chosen so far. To make the distances cheap, every vector is first projected from 1,024 to 128 numbers with a random
linear map. The projection is used only for choosing; the saved vectors are the original 1,024-number features.

**Input / output.** The fold's ordered bank rows. Output: `coreset_<fold>_seed<s>_indices.npy` (24,000 row
numbers), `..._vectors.npy` (24,000 x 1,024 float32), and a JSON record with the seed, sizes, source frames, method
and hashes.

**What can go wrong.** A different input order or an extra random-number call changes the coreset without anyone
noticing; that acts like a hidden extra seed. Moving all 2.4 million rows to the GPU at once runs out of memory,
which is why the projection is chunked (D5).

**Tests.** `tests/test_stage2_coreset.py`: the chunked projection gives exactly the official sampler's indices on
synthetic features; the same seed gives the same coreset and a different seed a different one; the projection
weights equal the official ones; saved coresets are refused if a byte changes. On Kaggle, seed 0 is built twice
and must give identical indices.

## 4. Anomaly maps (`src/tsfpilot/scoring.py`)

**What it does.** For each cell, the squared distance to its nearest coreset vector:
`a = min_b max(0, ||q||^2 + ||b||^2 - 2 q.b)`, in float32, 2,000 queries at a time. The 8,000 values form the raw
80 x 100 map; the frame score is its maximum.

**Why squared.** It is what the official code returns (faiss `IndexFlatL2`), and averaging squared distances over
aligned frames is averaging log-likelihood-type evidence. This was frozen in v1.1 and is not revisited.

**What can go wrong.** The expansion subtracts two large numbers when a query is close to a coreset vector, so float32
loses digits. TF32 or float16 would make it worse. **This is the main numerical risk of Stage 2**: AT-03 compares the
float32 result with a float64 brute-force computation and requires the largest error to stay under 1e-4 of the
largest distance. AT-03 now records the query norms and distances it saw, so if it fails we can tell whether the
cause is cancellation or a bug.

**Guard.** `anomaly_maps` refuses any batch whose purpose is not `validation`.

**Tests.** `tests/test_stage2_scoring.py`: against float64 brute force, chunking invariance, map shape, and the
purpose guard.

## 5. Motion and tau_r (`src/tsfpilot/stage2_motion.py`)

**What it does.** Runs phase correlation (Stage 1's `motion.raw_scenario`) on every frame pair of each training-side
scenario, saves dx, dy and the response r, and computes tau_r per fold with Stage 1's `motion.tau_r`. Then it
computes the statuses (reliable, held, unknown), k_t and K_t of the validation scenario under each fold's tau_r.

**Why.** V4 needs to know how far the fabric moved between frames. Phase correlation is sometimes wrong (dark or
blurred frames). tau_r is the response level above which the estimates are trustworthy, chosen on training-side
scenarios only, without any detector output.

**Idea.** Phase correlation finds the shift between two images from the phase of their Fourier transforms; the peak
height r says how clear the answer is. tau_r is the smallest r on a 0.01 grid at which at least 1,000 pairs pass and
95% of them agree with their neighbours.

**What can go wrong.** Including the fold's own test group (the gate forbids it); confusing raw estimates with
statuses. `T1_S164_I199_1` is noisy (forensic table: dx IQR 200 px, median response 0.50), so many of its frames may
be held or unknown. Since v1.2.2 it is not used by AT-06b, and it never enters a decision.

**Tests.** `tests/test_stage2_validation.py::test_tau_r_record_counts_agree_with_the_rule` and the access tests.

## 6. Validation constants (`src/tsfpilot/validation.py`)

**What they are, per fold and seed:**

- `mu0`: the mean map value over all 1,212 x 8,000 validation cells. It fills the columns that V4 cannot read
  because that fabric was not yet visible.
- `b1`, `b3`: per-cell mean map and mean 3 x 3 maximum map (for the exploratory C6 analysis).
- `tau_cell`: the 99.9th percentile of all validation cells (v1.1 definition, DL-0013). No v1.2 rule uses it; AT-04c
  checks that it reproduces.
- `b1` column profile: the left-right shape of the average map. Every test scenario moves left, so a left-right
  asymmetry would affect C-REV; it is reported before any test frame is scored.
- Deployment thresholds: for each variant, the lowest threshold that gives at most 2 false-alarm events per 1,000
  validation frames (section 14 rule on the validation timeline). A diagnostic for S9.

**Why per seed.** A different coreset gives different maps, so its constants differ too (section 8).

**Tests.** Known maps give the exact mean, percentile and border-clipped maximum; non-float32 or non-finite maps are
refused; the threshold rule agrees with a brute-force definition on 20 random timelines with ties.

## 7. Acceptance tests (`src/tsfpilot/acceptance2.py`)

| Test | Question it answers | Pass rule |
|---|---|---|
| AT-01 | Are the shapes right at full resolution? | layer2 (1, 512, 80, 100), layer3 (1, 1024, 40, 50), features (8000, 1024), map (80, 100) |
| AT-02 | Is our feature path the official PatchCore path? | max rel <= 1e-5 against `PatchCore._embed`, frames 1 to 5 |
| AT-03 | Is the float32 distance accurate? | max error <= 1e-4 of the largest float64 distance, 2,000 cells of frame 1, per fold; if that fails, every query within the float32 rounding bound (v1.2.2 C3) |
| AT-04a | Is the run deterministic? | frames 1 to 10 twice, identical batches: bit-identical maps, all six coresets |
| AT-04b | Does the batch size matter? | batch 1 vs batch 4: features rel <= 1e-6 and maps rel <= 1e-4 (v1.2.2 C2) |
| AT-06b | Does the warp point the right way on real frames? | per fold, on T1_S164_I192_1 then T1_S164_I193_1, the U-warp beats the -U warp on >= 190 of 200 pairs (v1.2.2 C4) |

AT-06b in plain words: average each frame to 80 x 100, shift the previous frame by the measured motion, and check
that it matches the current frame better than shifting it the other way. If the sign convention were flipped
anywhere, V4 would be averaging the wrong fabric and this test would fail.

**What changed in v1.2.2 and why.** Run 1 showed three tests that could not work as written (DL-0015). AT-04b's
map limit of 1e-6 is below what float32 can deliver for a squared distance: a 1e-7 difference in the features is
multiplied by about 2 x ||q||^2 / distance. AT-03 has the same weakness at full coreset size, so it gained a fallback
that compares each error with the worst-case float32 rounding bound. That bound is loose: it catches a wrong
computation, not a slightly imprecise one. AT-06b moved from the validation scenario, whose fabric pattern repeats
about every 85 px and makes the warp direction ambiguous, to the two G2 scenarios with clean motion. The pairs are
chosen from the motion statuses and written to a file before any image is opened, so the choice cannot depend on
what the images show.

## 8. The runner (`scripts/run_stage2.py`) and the notebook

The runner checks the frozen hashes (preregistration, amendment, config, bank record, Stage 1 report), then runs
phases 0, A, B, C, D, E. Each phase writes `phase_<X>.json`; rerunning skips finished phases, and the run stops at
the first failed phase. `--smoke` caps every size so the whole chain runs in minutes; a smoke report is never the
record. The notebook runs a smoke pass first, then the run of record, then prints a summary and zips the small
record files.

**What you can run yourself without a GPU or the dataset:**

```bash
pip install -r requirements.txt
pip install torch torchvision faiss-cpu timm      # CPU builds are enough for the unit tests
python -m pytest -q tests/test_stage2_*.py tests/test_third_party_pin.py
```

## 9. How to approach problems like this

- Write down which data each step may touch, then make the code enforce it.
- When you reimplement a published method, keep the original code next to yours and test one against the other.
- Seed everything immediately before the random step, record the seed, and rebuild once to prove it reproduces.
- For every number you will reuse later, save it with its hash and the code that produced it.
- When a tolerance fails, record enough to explain why before touching anything. Never move the tolerance.
