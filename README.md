# TSFabrics alignment pilot

A pre-registered, falsifiable pilot on the TSFabrics knitted-fabric video dataset. It asks whether averaging
normal-only (PatchCore-derived) anomaly maps after aligning them to the measured fabric motion (V4) changes false
alarms and missed defects, compared with frame scores (V0), score smoothing (V1), unaligned map averaging (V2) and
two controls that break only the correspondence (reversed alignment, lag permutation).

The specification is `PREREGISTRATION.md` (Research Gate v1.2) plus `PREREGISTRATION_AMENDMENT_v1.2.1.md`.
Every module in `src/tsfpilot/` names the section it implements. If a behaviour is not in those two documents,
it is not in the code.

## Status

| Stage | What | Status |
|---|---|---|
| Stage 1 | Synthetic data, reference scripts, frozen CSVs, label files. CPU. No images | **PASS** on Kaggle, 2026-10-04: 53 passed, 0 failed, 0 skipped (record in `audit/stage1_kaggle/`, decision log DL-0012) |
| Stage 2 | Bank and validation frames only: features, coresets, validation constants, tau_r. GPU | Not yet implemented |
| Stage 3 | One locked run on the test folds | Not yet implemented |

## Layout

```text
PREREGISTRATION.md                 Research Gate v1.2 (frozen; SHA-256 recorded in the config)
PREREGISTRATION_AMENDMENT_v1.2.1.md  C0b offset amendment (adopted 2026-10-01)
configs/pilot_v1_2_1.yaml          every constant; the loader refuses unknown or missing keys
data/frozen/                       passes and tracks, condition clusters, bank audit, forensic summary
reference/                         frozen v1.2 reference scripts (never imported by src/)
calibration/c0b/                   C0b calibration package: protocol, addendum, code, results
src/tsfpilot/                      the pipeline
tests/                             pytest; one file per acceptance-test group (AT-05 to AT-17)
scripts/run_stage1.py              runs Stage 1 and writes audit/stage1_report.json
notebooks/stage1_kaggle.ipynb      thin Kaggle launcher
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
run all cells. The result must be `PASS` before Stage 2 starts.

## Rules the code enforces

- Exact rational arithmetic for every decision quantity; thresholds are compared on q9 (half-even, 9 places).
- Stages are sealed: Stage 1 opens no image; Stage 2 never scores a test frame; Stage 3 runs once.
- Any NaN or infinity in a score aborts the run.
- Seeds, generator calls and summation orders are fixed and documented.
