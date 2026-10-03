"""REFERENCE (audit): C0b offset generator as amended by v1.2.1 (section C1, C2 of the amendment).
Offsets are uniform on the full cyclic group {0, ..., N_s - 1} of each scenario.
The collapse rule is unchanged from ref_chance.collapsed (k >= 10 of 200)."""
import hashlib
import numpy as np
from fractions import Fraction as Fr

NSHIFT = 200


def draw_offsets_v121(scen_specs, fold_idx, seed_idx):
    """scen_specs: list of (scenario_id, N, P) in lexicographic scenario order -> int64 array (200, n_scen)."""
    rng = np.random.Generator(np.random.PCG64([20260925, fold_idx, seed_idx]))
    cols = [rng.integers(0, N, NSHIFT) for _, N, _ in scen_specs]
    return np.stack(cols, 1).astype(np.int64)


def offsets_sha256(O):
    return hashlib.sha256(np.ascontiguousarray(O, dtype=np.int64).tobytes()).hexdigest()


def collapsed(p3_obs, p3_null):
    k = sum(1 for v in p3_null if v >= p3_obs)
    return k >= 10, Fr(1 + k, 1 + len(p3_null))
