"""Motion estimation (section 7). Label-free; causal except the oracle (item 9, diagnostic only).

Raw estimate for frame t (t >= 2): (dx, dy), r = cv2.phaseCorrelate(P.copy(), C.copy(), W) on the standardised
crop of rows 32..607, with P = frame t-1, C = frame t and W a Hanning window. Sign convention:
I_t(x) = I_(t-1)(x - dx_t), so leftward fabric motion gives dx < 0.

Implementation note (logged in docs/UNRESOLVED.md, U-I1): v1.2 section 7 item 5 calls every non-reliable frame
other than frame 1 'held' when t - last_reliable <= 5. A frame without an estimate (std < 1e-6, or after such a
frame) is non-reliable and is treated by that rule. The v1.1 pseudo-code E2 marked such frames 'unknown'. No pilot
test scenario contains such frames, so the choice cannot affect the pilot; the v1.2 text is followed.
"""
import numpy as np

RELIABLE, HELD, UNKNOWN = 2, 1, 0

_WIN_CACHE = {}


def hanning(width=800, height=576):
    import cv2
    key = (width, height)
    if key not in _WIN_CACHE:
        _WIN_CACHE[key] = cv2.createHanningWindow((width, height), cv2.CV_32F)
    return _WIN_CACHE[key]


def standardise(img_u8, crop_rows=(32, 607), std_min=1e-6):
    """uint8 [640, 800] -> standardised float32 crop [576, 800], or None if the crop is (near) constant."""
    a, b = crop_rows
    x = np.asarray(img_u8)[a:b + 1, :].astype(np.float32)
    m = float(x.mean())
    s = float(x.std())                       # population standard deviation
    if s < std_min:
        return None
    return ((x - m) / s).astype(np.float32)


def phase_correlate(prev_z, cur_z, win=None):
    """Return (dx, dy, r). Inputs are copied because cv2.phaseCorrelate may modify them (pre-implementation audit)."""
    import cv2
    if win is None:
        win = hanning(prev_z.shape[1], prev_z.shape[0])
    (dx, dy), r = cv2.phaseCorrelate(prev_z.copy(), cur_z.copy(), win)
    return float(dx), float(dy), float(r)


def raw_scenario(frames, crop_rows=(32, 607), std_min=1e-6):
    """frames: iterable of uint8 images in frame order (t = 1..N).
    Returns float64 arrays dx, dy, r and bool has_est (index 0 = frame 1, which never has an estimate)."""
    dx, dy, r, has = [], [], [], []
    prev = None
    win = None
    for t, img in enumerate(frames, start=1):
        z = standardise(img, crop_rows, std_min)
        if t == 1 or z is None or prev is None:
            dx.append(np.nan); dy.append(np.nan); r.append(np.nan); has.append(False)
        else:
            if win is None:
                win = hanning(z.shape[1], z.shape[0])
            a, b, c = phase_correlate(prev, z, win)
            dx.append(a); dy.append(b); r.append(c); has.append(True)
        prev = z
    return np.array(dx), np.array(dy), np.array(r), np.array(has)


def _consistent(x, hist, mcfg):
    med = float(np.median(hist[-mcfg["consistency_window"]:]))
    return abs(x - med) <= max(mcfg["consistency_abs"], mcfg["consistency_rel"] * abs(med))


def statuses(dx_raw, dy_raw, r_raw, has_est, tau_r, mcfg):
    """Section 7 items 4 and 5. Returns (status int8 array, dx float64 array: reliable dx, held = last reliable dx,
    unknown = nan). tau_r None means motion-invalid fold: every frame is unknown."""
    n = len(dx_raw)
    st = np.full(n, UNKNOWN, np.int8)
    dxv = np.full(n, np.nan)
    if tau_r is None:
        return st, dxv
    hist = []
    last_rel = None
    for i in range(n):
        t = i + 1
        ok = False
        if t > 1 and has_est[i]:
            ok = (r_raw[i] >= tau_r and abs(dx_raw[i]) <= mcfg["max_abs_dx"] and abs(dy_raw[i]) <= mcfg["max_abs_dy"])
            if ok and len(hist) >= mcfg["consistency_min_history"]:
                ok = _consistent(dx_raw[i], hist, mcfg)
        if ok:
            st[i] = RELIABLE
            dxv[i] = dx_raw[i]
            hist.append(float(dx_raw[i]))
            last_rel = i
        elif t > 1 and last_rel is not None and (i - last_rel) <= mcfg["hold_frames"]:
            st[i] = HELD
            dxv[i] = dxv[last_rel]
    return st, dxv


def tau_r(scenarios_raw, mcfg):
    """Section 7 item 3. scenarios_raw: list of (dx, dy, r, has_est) for every training-side scenario of the fold.
    Smallest tau on the 0.01 grid with >= 1000 pairs having r >= tau and >= 95% of those consistent.
    Consistency uses the median of the previous up to 15 pairs of the scenario (any r), once >= 5 exist."""
    rs, cons = [], []
    for dx, dy, r, has in scenarios_raw:
        prev = []
        for i in range(len(dx)):
            if not has[i]:
                continue
            c = abs(dx[i]) <= mcfg["max_abs_dx"] and abs(dy[i]) <= mcfg["max_abs_dy"]
            if c and len(prev) >= mcfg["consistency_min_history"]:
                c = _consistent(dx[i], prev, mcfg)
            rs.append(r[i]); cons.append(c)
            prev.append(float(dx[i]))
    rs = np.asarray(rs); cons = np.asarray(cons, bool)
    steps = int(round(1 / mcfg["tau_r_grid_step"]))
    for g in range(steps + 1):
        tau = g / steps
        sel = rs >= tau
        n = int(sel.sum())
        if n >= mcfg["tau_r_min_pairs"] and 100 * int(cons[sel].sum()) >= 95 * n:
            return tau
    return None


def oracle_dx(dx, status, mcfg):
    """Section 7 item 9: median of reliable dx over [j - 15, j + 15] with at least 5 values; else nan (unknown)."""
    n = len(dx)
    h = mcfg["oracle_halfwidth"]
    out = np.full(n, np.nan)
    rel = status == RELIABLE
    for j in range(n):
        a, b = max(0, j - h), min(n, j + h + 1)
        v = dx[a:b][rel[a:b]]
        if len(v) >= mcfg["oracle_min_values"]:
            out[j] = float(np.median(v))
    return out


def motion_unknown(known, K):
    """Section 7 item 7: frame t (1-based) is motion-unknown if any j in [t - K_t + 2, t] is not known.
    known: bool per frame; K: int per frame. Returns bool array."""
    n = len(known)
    bad = ~np.asarray(known, bool)
    cb = np.concatenate([[0], np.cumsum(bad)])
    out = np.zeros(n, bool)
    for i in range(n):
        t = i + 1
        lo = max(1, t - int(K[i]) + 2)
        out[i] = (cb[t] - cb[lo - 1]) > 0 if lo <= t else False
    return out
