"""AUDIT: repaired C6 decomposition (v1.2 candidate) on synthetic 80x100 maps. Exploratory-rule check only."""
import numpy as np, c6_synth as S
from collections import Counter
vmax = S.val.reshape(len(S.val), -1).max(1); TAU = np.quantile(vmax, 0.99); MEDB1 = np.median(S.b1)
FLOOR = 0.1 * (TAU - MEDB1)
def classify(maps, te, u0, K):
    a = maps[te]; s = a.max()
    if s < TAU: return None                                   # not an FA event at this threshold
    if s - (np.median(a) - MEDB1) < TAU: return 'global-driven'
    ys, xs = np.unravel_index(np.argmax(a), a.shape); E0 = a[ys, xs] - S.b1[ys, xs]
    path = []
    for j in range(1, K + 1):
        x = xs - int(np.floor(j * u0 + 0.5))
        if not (0 <= x <= 99) or te + j >= len(maps): break
        path.append((j, x))
    if len(path) < 3 or E0 < FLOOR: return 'ambiguous (J<3 or E0<floor)'
    if all(abs(x - xs) <= 1 for _, x in path): return 'ambiguous (camera and fabric paths coincide)'
    M = {j: S.M3(maps[te + j]) for j, _ in path}
    rho = np.median([(M[j][ys, x] - S.b3[ys, x]) / E0 for j, x in path])
    rho0 = np.median([np.mean([M[j][r, x] - S.b3[r, x] for r in (ys + 10, ys - 10) if 0 <= r < 80]) / E0 for j, x in path])
    rcam = np.median([(M[j][ys, xs] - S.b3[ys, xs]) / E0 for j, _ in path])
    if rho0 >= 0.25: return 'diffuse'
    if rcam >= 0.5 and rcam - rho0 >= 0.25 and rcam > rho: return 'camera-fixed'
    if rho >= 0.5 and rho - rho0 >= 0.25: return 'persistent-local'
    if rho < 0.25 and rcam < 0.25: return 'transient'
    return 'ambiguous'
def run(kind, u0, K, A=14.0):
    n = K + 3; m = S.noise(n); y = int(S.rng.integers(15, 65)); x0 = float(S.rng.integers(60, 95))
    if kind == 'pure noise': pass
    elif kind == 'global elevation (+1.25 SD)': m += 2.5
    elif kind == 'transient (1 frame)': S.blob(m, 0, y, x0, A)
    elif kind == 'persistent fabric-fixed': [S.blob(m, t, y, x0 - t * u0, A) for t in range(n)]
    elif kind == 'camera-fixed': [S.blob(m, t, y, x0, A) for t in range(n)]
    elif kind == 'persistent, exit-edge start': [S.blob(m, t, y, 20 - t * u0, A) for t in range(n)]
    elif kind == 'persistent, late peak': [S.blob(m, t, y, x0 - t * u0, A * (0.6 + 0.25 * t)) for t in range(n)]
    elif kind == 'vertical line, fabric-fixed':
        for t in range(n):
            x = int(round(x0 - t * u0))
            if 0 <= x < 100: m[t, :, max(0, x - 1):x + 2] += A * 0.6; m[t, y, max(0, x - 1):x + 2] += A * 0.4
    return classify(m, 0, u0, K)
kinds = ['pure noise', 'global elevation (+1.25 SD)', 'transient (1 frame)', 'persistent fabric-fixed', 'camera-fixed',
         'persistent, exit-edge start', 'persistent, late peak', 'vertical line, fabric-fixed']
for label, u0, K in [('A-G1 speed', 14.0, 7), ('A-G4 speed', 4.75, 21), ('slow fabric', 0.8, 21)]:
    print(f"\n{label}: u0={u0} cells/frame, K={K}  (counts over events only)")
    for k in kinds:
        c = Counter(r for r in (run(k, u0, K) for _ in range(80)) if r is not None)
        print(f"  {k:30s}", dict(c))
