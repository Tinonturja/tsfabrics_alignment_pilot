"""REFERENCE (audit): circular-shift chance baseline for C0b (Research Gate v1.2 section 19)."""
import numpy as np
from fractions import Fraction as Fr
NSHIFT = 200
def allowed_offsets(N, P, phase_restrict=True):
    d = np.arange(-(-N // 4), (3 * N) // 4 + 1)            # ceil(N/4) .. floor(3N/4)
    if phase_restrict:
        r = d % P; d = d[(r >= -(-P // 4)) & (r <= (3 * P) // 4)]
    return d[d != 0]
def draw_offsets(scen_specs, fold_idx, seed_idx, phase_restrict=True):
    """scen_specs: list of (scenario_id, N, P) in lexicographic scenario order -> array (NSHIFT, n_scen)."""
    rng = np.random.Generator(np.random.PCG64([20260925, fold_idx, seed_idx]))
    cols = []
    for _, N, P in scen_specs:
        a = allowed_offsets(N, P, phase_restrict); cols.append(a[rng.integers(0, len(a), NSHIFT)])
    return np.stack(cols, 1)
def collapsed(p3_obs, p3_null):
    """Collapse iff at least 10 of the 200 shifted P3 values are >= the observed P3 (p = (1+#)/(201) > 0.05)."""
    k = sum(1 for v in p3_null if v >= p3_obs)
    return k >= 10, Fr(1 + k, 1 + len(p3_null))
