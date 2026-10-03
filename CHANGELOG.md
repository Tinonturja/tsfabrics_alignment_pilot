# Changelog

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
