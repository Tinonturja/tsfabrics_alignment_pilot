# Open questions

Reviewed at every stage gate. Nothing leaves this list without a dated note saying how it was closed.

| # | Question | Why it matters | How to close it | Status |
|---|---|---|---|---|
| U1 | What does MAP-VD's "cross match-guided" step do? | Could move a class D novelty claim to class B | Read the CVF PDF method section | Open |
| U2 | Does Lu et al. 2022 align frames in pre-processing? | Same risk for the fabric-video claim | Read their Section 3 | Open |
| U3 | GeoMAD (arXiv 2608.26724): what does it align? | Possible overlap | Read the PDF | Open |
| U4 | IEEE document 9199891 | Probably spatial, not temporal; unconfirmed | Open the IEEE page | Open |
| U5 | Does the real V0 trace carry a rotation-periodic component as strong as calibration null N6? | Sets how much of the residual 6% C0b excess applies | Report V0 autocorrelation at lag P_s descriptively after Stage 3; no rule change | Open (Stage 3) |
| U6 | Does the scenario-median-k window approximation used in the calibration change the C0b result? | The calibration used median-k windows, Stage 3 uses adaptive K_t | After Stage 3, rerun calibration cells N1 and N3 on the actual windows (descriptive only; no rule change). Low risk: windows differ by a few frames | Open (after Stage 3) |
| U7 | Has anyone published normal-only results on TSFabrics? | Time-sensitive novelty | Re-check citations before submission | Open |
| U8 | Will the few-cluster bootstrap CI matter for C3? | Declared limitation | Nothing before Stage 3 | Declared |
| U-I1 | Section 7: status of frames with no estimate (v1.2 text vs v1.1 pseudo-code E2) | Specification ambiguity | Followed the v1.2 text (DL-0009 I-1); cannot affect the pilot test scenarios. Stage 2 counts constant-crop frames on training-side scenarios; the Stage 3 runner logs the count on test scenarios (a count, never a score) | Open (Stage 2 check) |
| U-I2 | Kaggle numpy version vs the AT-15 fixture (numpy 2.4.4) | PCG64 `integers` output must match the fixture | Run AT-15 on Kaggle; if it fails, pin numpy 2.4.4 | Open (Stage 1 on Kaggle) |
