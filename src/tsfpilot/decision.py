"""Criteria and decision machine (sections 20, 21, 22). Pure Python; every comparison on q9 of exact values.

Per-fold input dict (one coreset seed):
  flags: {'collapse': bool, 'motion': bool, 'saturated': bool}
  P3:    {'V1', 'V4', 'V2', 'REV', 'LAG': Fraction}
  P2:    {'V1', 'V4': Fraction}
  P1:    {'V1', 'V4': (Fraction value capped at 50, censored bool)}
  LB:    LB_f (Decimal, already q9) or any number; compared as q9(LB) > 0
This module is written from the text of the specification and is checked against reference/ref_decision.py (AT-12).
"""
from .exact import D, q9, sign9

BAND = D("0.02")
C1_PASS, C1_FAIL = D("0.80"), D("0.95")
C2_MIN = D("0.06")
S_PASS, S_FAIL = D("0.5"), D("0.2")
CONTROLS = ("V2", "REV", "LAG")
SEVERITY = ("G", "M", "F", "D", "E", "C", "I", "A")


def validity(flags):
    """Section 20: one ordered chain, collapse > motion > saturated > valid."""
    if flags["collapse"]:
        return "collapse"
    if flags["motion"]:
        return "motion"
    if flags["saturated"]:
        return "saturated"
    return "valid"


def band(dp3):
    v = q9(dp3)
    if v <= -BAND:
        return "harm"
    if v >= BAND:
        return "positive"
    return "null"


def gain(f):
    return f["P3"]["V4"] - f["P3"]["V1"]


def control_status(f, c):
    G = gain(f)
    m = f["P3"]["V4"] - f["P3"][c]
    S = m / G                               # only called when q9(G) >= 0.02, so G != 0
    if q9(S) <= S_FAIL:
        return "fail"
    if q9(S) >= S_PASS and q9(m) >= BAND:
        return "pass"
    return "between"


def c4_fold(f):
    st = [control_status(f, c) for c in CONTROLS]
    if "fail" in st:
        return "fail"
    if all(s == "pass" for s in st):
        return "pass"
    return "between"


def c1_fold(f):
    (a, ca), (b, cb) = f["P1"]["V1"], f["P1"]["V4"]
    if q9(a) == 0 and q9(b) == 0:
        return "nonevaluable"
    if q9(a) == 0:                          # P1(V1) = 0 < P1(V4)
        return "fail"
    if ca and cb:
        return "nonevaluable"
    r = q9(b / a)
    if r <= C1_PASS:
        return "pass"
    if r > C1_FAIL:
        return "fail"
    return "between"


def c2_fold(f):
    return q9(f["P2"]["V4"] - f["P2"]["V1"]) >= C2_MIN


def c7(f1, f2):
    keys = ["dP3", "dP2"]
    if c1_fold(f1) != "nonevaluable" and c1_fold(f2) != "nonevaluable":
        keys.append("d1")
    for k in keys:
        s = []
        for f in (f1, f2):
            if k == "dP3":
                s.append(sign9(gain(f)))
            elif k == "dP2":
                s.append(sign9(f["P2"]["V4"] - f["P2"]["V1"]))
            else:
                s.append(sign9(f["P1"]["V1"][0] - f["P1"]["V4"][0]))
        if s[0] * s[1] == -1:
            return False
    return True


def criteria(f1, f2):
    b = [band(gain(f)) for f in (f1, f2)]
    c4 = [c4_fold(f) if bb == "positive" else None for f, bb in zip((f1, f2), b)]
    return {
        "band": b,
        "C1": all(c1_fold(f) == "pass" for f in (f1, f2)),
        "C1_fold": [c1_fold(f) for f in (f1, f2)],
        "C2": all(c2_fold(f) for f in (f1, f2)),
        "C3": b == ["positive", "positive"] and any(q9(f["LB"]) > 0 for f in (f1, f2)),
        "C4": b == ["positive", "positive"] and all(x == "pass" for x in c4),
        "C4_fold": c4,
        "C7": c7(f1, f2),
    }


def decide(f1, f2):
    """Section 22, one coreset seed. Returns one of A, B, Bstar, C, D, E, F, G, M."""
    val = [validity(f["flags"]) for f in (f1, f2)]
    n_invalid = sum(v != "valid" for v in val)
    if n_invalid == 2:
        if "collapse" in val:
            return "G"
        if "motion" in val:
            return "M"
        return "F"
    if n_invalid == 1:
        return "Bstar"
    cr = criteria(f1, f2)
    if "harm" in cr["band"]:
        return "D"
    if cr["band"] == ["null", "null"]:
        return "C"
    if any(bb == "positive" and c == "fail" for bb, c in zip(cr["band"], cr["C4_fold"])):
        return "E"
    if cr["C3"] and cr["C4"] and cr["C7"] and (cr["C1"] or cr["C2"]):
        return "A"
    return "B"


def final(o0, o1, o2):
    """Seed follow-up: C, D, E, F, G, M at seed 0 are final; otherwise B and B* map to I and the most severe
    outcome across seeds 0 to 2 wins (G > M > F > D > E > C > I > A)."""
    if o0 not in ("A", "B", "Bstar"):
        return o0
    mapped = ["I" if o in ("B", "Bstar") else o for o in (o0, o1, o2)]
    return min(mapped, key=SEVERITY.index)
