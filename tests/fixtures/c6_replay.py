"""Replays reference/audit_b7_c6.py draw for draw, classifying with tsfpilot.decomposition. Prints JSON counts.
Run in a fresh process: importing reference/c6_synth consumes its RNG in a fixed order."""
import contextlib, io, json, os, sys
from collections import Counter
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "reference")); sys.path.insert(0, os.path.join(REPO, "src"))
with contextlib.redirect_stdout(io.StringIO()):
    import c6_synth as S
from tsfpilot import config
from tsfpilot.decomposition import classify
DC = config.load()["decomposition"]
vmax = S.val.reshape(len(S.val), -1).max(1); TAU = np.quantile(vmax, 0.99)
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
    if m[0].max() < TAU:
        return None
    return classify(m, 0, K, np.full(n, -u0), np.ones(n, bool), S.b1, S.b3, TAU, DC)
kinds = ['pure noise', 'global elevation (+1.25 SD)', 'transient (1 frame)', 'persistent fabric-fixed', 'camera-fixed',
         'persistent, exit-edge start', 'persistent, late peak', 'vertical line, fabric-fixed']
out = {}
for label, u0, K in [('A-G1 speed', 14.0, 7), ('A-G4 speed', 4.75, 21), ('slow fabric', 0.8, 21)]:
    for k in kinds:
        c = Counter(r for r in (run(k, u0, K) for _ in range(80)) if r is not None)
        out[f"{label}|{k}"] = dict(c)
print(json.dumps(out))
