# Changelog

## 0.2.0 (2026-10-05): Stage 2 implementation

- Stage 2 implementation audit (`docs/stage2/STAGE2_IMPLEMENTATION_AUDIT.md`) and clarifications DL-0013:
  tau_cell and deployment thresholds take their v1.1 definitions; AT-06b, AT-03 and fixture choices fixed.
- Official PatchCore files copied byte-for-byte from `fcaa92f` into `third_party/patchcore/`, with a blob-id test.
- New modules: `access` (purpose-tagged frame gate), `detector` (feature path, D1 to D4), `coreset` (official
  sampler with the chunked projection, D5), `scoring` (squared L2 1-NN, D6), `stage2_motion` (raw motion, tau_r,
  validation statuses), `validation` (mu0, b1, b3, tau_cell, profile, deployment thresholds), `acceptance2`
  (AT-01, AT-02, AT-03, AT-04a, AT-04b, AT-06b), `official` (pinned imports).
- `scripts/run_stage2.py` (phases 0, A to E, resumable, smoke mode) and `notebooks/stage2_kaggle.ipynb`.
- CPU tests: access rules, feature path against the official `PatchCore._embed`, coreset equivalence and
  reproducibility, distances against float64, validation constants, deployment rule, AT-06b logic, section 23
  numbers. A CPU smoke run of the whole chain on synthetic frames completed (not a record).

## 0.1.0 (2026-10-03): Stage 1 implementation

- Repository scaffold, preregistration v1.2, amendment v1.2.1, decision log, open questions.
- Frozen reference scripts (`reference/`) and the C0b calibration package (`calibration/c0b/`).
- Pipeline modules for every Stage 1 and CPU-side Stage 3 step: config, exact, frames, bank, motion, windows,
  variants, passes, events, metrics, chance (v1.2.1), bootstrap, decision, decomposition, manifest.
- Acceptance tests AT-05 to AT-17 plus section 4, 11 and 18 unit tests. Sandbox run: 48 passed, 3 skipped
  (AT-14 needs the dataset's label files).
- After an independent code audit: added `motion.motion_invalid` (C0c) and a test that code constants equal the YAML.
- Pre-Kaggle audit (2026-10-04): isolated, checked package install in the Kaggle notebook; location-independent `layout.py` path; wider Stage 1 report hashes; `HASHES_NOTE.md`.
- Stage 1 record (2026-10-04): PASS on Kaggle, 53 of 53 tests, files fingerprint matching the committed tree (DL-0012).
- Not yet implemented: Stage 2 (detector, coreset, scoring, validation constants, tau_r run) and the Stage 3
  runner and report.
