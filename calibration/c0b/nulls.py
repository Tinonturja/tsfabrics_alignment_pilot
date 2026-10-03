"""CALIBRATION CODE. Information-free score-trace generators (independent of labels), per PROTOCOL.md."""
import numpy as np
from scipy.signal import lfilter


def ar1(rng, n, phi, sd_innov=None):
    e = rng.normal(size=n)
    if sd_innov is None:
        sd_innov = np.sqrt(1 - phi ** 2)          # unit stationary variance
    return lfilter([1.0], [1.0, -phi], e * sd_innov)   # burn-in handled by ar1_burn


def ar1_burn(rng, n, phi, sd_innov=None, burn=None):
    burn = burn if burn is not None else int(min(5000, 5 / (1 - phi)))
    return ar1(rng, n + burn, phi, sd_innov)[burn:]


def periodic(rng, n, P, amp):
    prof = np.convolve(rng.normal(size=P + 20), np.ones(9) / 9, 'same')[10:10 + P]
    prof = amp * (prof - prof.mean()) / (prof.std() + 1e-12)
    phase = int(rng.integers(0, P))
    return prof[(np.arange(n) + phase) % P]


def gen(family, rng, Ns, Ps):
    out = []
    for N, P in zip(Ns, Ps):
        N = int(N); P = int(P)
        if family == 'N1_iid':
            x = rng.normal(size=N)
        elif family == 'N2_ar0.9':
            x = ar1_burn(rng, N, 0.9)
        elif family == 'N3_ar0.99':
            x = ar1_burn(rng, N, 0.99)
        elif family == 'N4_drift':
            x = ar1_burn(rng, N, 0.999, 0.0447) + 0.05 * rng.normal(size=N)
        elif family == 'N5_offsets':
            x = ar1_burn(rng, N, 0.9) + 2.0 * rng.normal()
        elif family == 'N6_periodic':
            x = ar1_burn(rng, N, 0.9) + periodic(rng, N, P, 1.0)
        elif family == 'N7_trend':
            x = ar1_burn(rng, N, 0.9) + rng.choice([-1, 1]) * np.linspace(-1, 1, N)
        elif family == 'N8_composite':
            x = (ar1_burn(rng, N, 0.95) + 1.0 * rng.normal() + periodic(rng, N, P, 0.7)
                 + ar1_burn(rng, N, 0.999, 0.0447))
        elif family == 'N9_ties':
            x = np.round(rng.normal(size=N) * 3) / 3        # about 20 distinct levels
        else:
            raise ValueError(family)
        out.append(x)
    return np.concatenate(out)


FAMILIES = ['N1_iid', 'N2_ar0.9', 'N3_ar0.99', 'N4_drift', 'N5_offsets', 'N6_periodic',
            'N7_trend', 'N8_composite', 'N9_ties']
