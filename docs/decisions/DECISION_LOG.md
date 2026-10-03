# Decision log

Each entry says what was decided, when, on what evidence, and whether any TSFabrics test-scenario detector output
existed at the time. Up to and including DL-0009, none did: no anomaly map, score or metric has been computed on any
frame of any scenario.

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
