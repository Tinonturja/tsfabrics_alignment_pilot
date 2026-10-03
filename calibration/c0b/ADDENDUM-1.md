# C0b calibration, Addendum 1 (written after the first primary FAILs, before any diagnostic or candidate run)

Date: 2026-09-30 (sandbox UTC clock). Trigger: primary run, fold A-G1, N3_ar0.99 FAIL (205/2000, CP95 0.0895-0.1166) and
N4_drift FAIL (344/2000, CP95 0.1557-0.1893). frac(k=200) was 0.024 and 0.0745 against 1/201 = 0.005 expected
under exchangeability, so BOTH tails are inflated. This points to a null distribution that is too narrow,
not only to a one-sided bias.

Two candidate mechanisms, stated before testing:
M1 (seam / cut): np.roll joins x[N-1] to x[0] and cuts the trace at the timeline edges; only the observed trace is uncut.
M2 (restricted, non-group offset set): all 200 offsets lie in [N/4, 3N/4] (and a phase band). With long-range
dependence the 200 shifted traces are strongly correlated WITH EACH OTHER but weakly with the observed (lag >= N/4),
so the observed is not exchangeable with the draws. A randomisation test with random transformations is exact when
the transformations are drawn uniformly from a group under which the null distribution is invariant; a band of
offsets that excludes the identity neighbourhood is not a group.

Pre-specified diagnostics (in addition to D1, D2 of PROTOCOL.md):
D3 seam-free nulls with the v1.2 restricted offsets: circular-stationary Gaussian AR traces (circulant covariance,
   FFT synthesis) with phi = 0.99 (C3) and phi = 0.999 (C4). No seam exists, so any FAIL here is caused by M2.
D4 candidate A1 on the same seam-free nulls: offsets uniform on {0..N_s-1} independently per scenario. Theory says exact.
Note on D1: giving the observed trace one random draw from the SAME restricted set makes it exchangeable with the
draws by construction, so D1 does not isolate M1 from M2. It is run as pre-registered but interpreted only as a
positive control.

Pre-specified amendment candidate (evaluated only on synthetic, label-independent traces):
A1: offsets for each scenario drawn uniformly from the full cyclic group {0, ..., N_s - 1}, independently per scenario,
    same generator PCG64([20260925, fold_index, seed_index]), same 200 draws, same collapse rule k >= 10.
    No threshold changes. Only the offset support changes.
A1 is accepted only if all 9 families x 2 folds PASS under the PROTOCOL.md decision rule (n = 2,000).

Power (secondary, not a selection criterion between rules that fail calibration): synthetic signal traces
x = AR(0.9) noise + delta * 1[frame inside a pass window], delta in {0.25, 0.5}, n = 500 per cell, both folds,
v1.2 rule vs A1. Reported so the cost of A1 is visible. A rule that fails calibration is not rescued by higher power.
