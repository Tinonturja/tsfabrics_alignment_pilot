# C0b calibration protocol (written before any calibration trace was generated)

Date: 2026-09-30. Status: pre-specified. No TSFabrics image, score or map is used.

Object calibrated: the frozen v1.2 C0b rule (section 19): 200 within-scenario circular shifts of the V0 score trace,
offsets from PCG64([20260925, fold_index, seed_index]) restricted to [ceil(N/4), floor(3N/4)] and to phase
(d mod P) in [ceil(P/4), floor(3P/4)]; collapsed iff at least 10 of 200 shifted P3 values are >= observed P3.
Layout: frozen pilot pass/track CSV; pass windows use the scenario-median k (approximation of the adaptive K_t; stated).
Metric: v1.2 P3 with ceil(L/25) events, exact integer arithmetic.

Quantity: false-pass rate = P(C0b says "not collapsed" | score trace carries no information about defect positions).
Design level under exact exchangeability: 10/201 = 0.04975.

Proposition used: P3 depends only on the ORDER of the scores (thresholds are the distinct values; alarm = score >= tau).
So the marginal distribution is irrelevant; only temporal dependence structure and ties matter. Null families therefore
vary dependence, non-stationarity, periodicity and ties.

Null families (all independent of labels; sd units of a unit-variance stationary AR component):
N1 iid Gaussian
N2 AR(1) phi=0.9
N3 AR(1) phi=0.99
N4 slow drift: AR(1) phi=0.999 (innovation sd 0.0447) + 0.05 iid
N5 scenario offsets: AR(0.9) + per-scenario level N(0, 2^2)
N6 rotation-periodic: AR(0.9) + fixed random profile of period P_s (smoothed noise, amplitude 1 sd), random phase
N7 within-scenario linear trend, random sign, total change 2 sd + AR(0.9)
N8 composite: AR(0.95) + offsets N(0,1) + periodic (0.7 sd) + drift
N9 ties: iid Gaussian rounded to 20 levels

Sample size: 2,000 independent traces per family per fold with seed-0 offsets (primary).
Clopper-Pearson 95% half-width at p=0.05 is about +/-1 percentage point. If the true rate is 0.05, P(upper bound <= 0.075) > 0.99.

Decision rule per (family, fold):
PASS if CP95 upper <= 0.075; FAIL if CP95 lower > 0.075; otherwise INDETERMINATE (then n is doubled once).
C0b is CALIBRATED if every (family, fold) passes. Any FAIL triggers diagnostics before any amendment:
D1 seam-matched observed (observed also receives one allowed shift): isolates the wrap seam.
D2 unrestricted offsets (no phase restriction): isolates the phase restriction.
Secondary (not decision-relevant): seeds 1 and 2 offsets (n=1,000, N1/N6/N8); power against weak real signal.
No v1.2 threshold or rule may be changed on the basis of this calibration except through a dated v1.2.1 amendment
that is justified by a FAIL under this protocol.
