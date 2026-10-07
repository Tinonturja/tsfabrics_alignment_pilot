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
| U-I2 | Kaggle numpy version vs the AT-15 fixture (numpy 2.4.4) | PCG64 `integers` output must match the fixture | Closed 2026-10-04: the Kaggle Stage 1 run installed numpy 2.4.4 and AT-15 passed (DL-0012) | Closed |
| U-S2a | Does the float32 distance expansion meet AT-03 (1e-4) and AT-04b (1e-6) on real validation data? | A CPU smoke run with random weights and near-duplicate frames gave about 5e-4 on AT-03, and faiss showed the same size of error. Real features may behave differently | Stage 2 run. If it fails, report the recorded diagnostics; any change to the distance computation is a methodological amendment and needs explicit authorisation | Run 1 smoke: AT-04b maps failed (1.1e-5 against 1e-6). Superseded by v1.2.2 C2 and C3 (DL-0016). Closed unanswered: the Stage 2 rerun stopped at phase A, so AT-03 and AT-04b never ran at full scale (DL-0024) |
| U-S2b | Does `T1_S164_I199_1` contain 200 consecutive reliable frames under each fold's tau_r? | Decides which AT-06b rule applies (DL-0013) | Stage 2 phase A | Closed by v1.2.2 C4: run 1 gave 92 of 200 on I199 (aliasing, DL-0015); AT-06b now uses I192 and I193 |
