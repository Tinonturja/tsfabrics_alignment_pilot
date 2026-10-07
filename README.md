# TSFabrics alignment pilot

A pre-registered, falsifiable pilot on the TSFabrics knitted-fabric video dataset. It asks whether averaging
normal-only (PatchCore-derived) anomaly maps after aligning them to the measured fabric motion (V4) changes false
alarms and missed defects, compared with frame scores (V0), score smoothing (V1), unaligned map averaging (V2) and
two controls that break only the correspondence (reversed alignment, lag permutation).

> **Outcome: stopped at Stage 2 (validation), as the protocol requires.** A motion-direction check failed (112 of
> 200 frame pairs, 190 required) because the validation fabric's pattern repeats about every 85 px while the fabric
> moves about 86 px per frame. Stage 3 never ran: no test label, anomaly map, score or metric was computed, so there
> is **no result about the research question**. Read the [technical note](docs/TECHNICAL_NOTE.md) for the
> two-page account, or the [final status report](docs/stage2/STAGE2_RERUN_AND_PILOT_STATUS.md) for the full record.

<p align="center"><img src="docs/figures/pilot_gates.svg" width="760" alt="Five gates: freeze the specification, calibrate on synthetic data, Stage 1 CPU tests (passed), Stage 2 GPU validation (failed at phase A), Stage 3 test (never run). A failure at any gate stops the pilot and is recorded; no re-tuning."></p>

The specification is `PREREGISTRATION.md` (Research Gate v1.2), `PREREGISTRATION_AMENDMENT_v1.2.1.md` and
`docs/stage2/AMENDMENT_v1.2.2_PROTOCOL.md`. Every module in `src/tsfpilot/` names the section it implements. If a
behaviour is not in those documents, it is not in the code.

## Status

| Stage | What | Status |
|---|---|---|
| Stage 1 | Synthetic data, reference scripts, frozen CSVs, label files. CPU. No images | **PASS** on Kaggle, 2026-10-04: 53 passed, 0 failed, 0 skipped (record in `audit/stage1_kaggle/`, decision log DL-0012) |
| Stage 2 | Bank and validation frames only: features, coresets, validation constants, tau_r. GPU | Run 1 failed at phase A (DL-0015). Amendment v1.2.2 adopted (DL-0016); its motion candidate failed calibration (DL-0017); C2 to C4 implemented (DL-0018). Stage 1 v1.2.2 PASS (DL-0022). Stage 2 rerun FAIL on AT-06b (DL-0024): **pilot stopped at Stage 2**; see `docs/stage2/STAGE2_RERUN_AND_PILOT_STATUS.md` |
| Stage 3 | One locked run on the test folds | **Not run.** Stopped by the v1.2.2 stop clause; test scenarios remain unscored (DL-0023, DL-0024) |

## Layout

```text
PREREGISTRATION.md                 Research Gate v1.2 (frozen; SHA-256 recorded in the config)
PREREGISTRATION_AMENDMENT_v1.2.1.md  C0b offset amendment (adopted 2026-10-01)
configs/pilot_v1_2_2.yaml          every constant (default config); the loader refuses unknown or missing keys
configs/pilot_v1_2_1.yaml          the v1.2.1 configuration, kept for the record
calibration/v1_2_2_m1/             M1 motion-candidate calibration (FAIL)
audit/                             Stage 1 and Stage 2 records, including failed runs (*_FAIL)
data/frozen/                       passes and tracks, condition clusters, bank audit, forensic summary
reference/                         frozen v1.2 reference scripts (never imported by src/)
calibration/c0b/                   C0b calibration package: protocol, addendum, code, results
src/tsfpilot/                      the pipeline
tests/                             pytest; one file per acceptance-test group (AT-05 to AT-17)
scripts/run_stage1.py              runs Stage 1 and writes audit/stage1_report.json
scripts/run_stage2.py              runs Stage 2 in resumable phases and writes stage2_report.json plus frozen/
notebooks/stage1_kaggle.ipynb      thin Kaggle launcher (Stage 1)
notebooks/stage2_kaggle.ipynb      thin Kaggle launcher (Stage 2, GPU)
third_party/patchcore/             official PatchCore files, byte-for-byte at fcaa92f (blob ids tested)
docs/TECHNICAL_NOTE.md             two-page account of the pilot and why it stopped
docs/stage2/                       Stage 2 audit, walkthrough, amendment v1.2.2, diagnosis and final status
docs/decisions/DECISION_LOG.md     dated decisions, including implementation choices
docs/UNRESOLVED.md                 open questions
docs/literature/                   novelty audit evidence
```

## Run Stage 1

Locally (without the dataset, AT-14 is skipped and the result is INCOMPLETE):

```bash
pip install -r requirements.txt
python scripts/run_stage1.py --allow-no-dataset
```

On Kaggle (the record): attach the TSFabrics dataset and this repository, open `notebooks/stage1_kaggle.ipynb`,
run all cells. The result must be `PASS` before Stage 2 starts. Under amendment v1.2.2 a new Stage 1 record is
made with `configs/pilot_v1_2_2.yaml`; it goes in `audit/stage1_kaggle_v1_2_2/` and its hash is pinned in
`scripts/run_stage2.py` before the Stage 2 rerun.

## Run Stage 2

Unit tests, anywhere (CPU builds of torch are enough):

```bash
pip install -r requirements.txt && pip install torch torchvision timm && pip install --no-deps -r requirements-stage2.txt
python -m pytest -q tests/test_stage2_*.py tests/test_third_party_pin.py
```

On Kaggle (the record): GPU accelerator, Internet on, attach the TSFabrics dataset and this repository, open
`notebooks/stage2_kaggle.ipynb`, and use Save & Run All. See `docs/stage2/STAGE2_WALKTHROUGH.md`.

## Rules the code enforces

- Exact rational arithmetic for every decision quantity; thresholds are compared on q9 (half-even, 9 places).
- Stages are sealed: Stage 1 opens no image; Stage 2 never scores a test frame; Stage 3 runs once.
- Any NaN or infinity in a score aborts the run.
- Seeds, generator calls and summation orders are fixed and documented.
