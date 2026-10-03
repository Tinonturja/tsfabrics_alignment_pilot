"""AT-12 (decision machine on the section 22 grid equals the reference; 0 invariant violations) and
AT-16 (section 21 boundary values, float and rational)."""
import collections
import itertools
import random
from decimal import Decimal
from fractions import Fraction as Fr

import pytest

from conftest import import_ref
from tsfpilot import decision as dec
from tsfpilot.exact import q9

ref = import_ref("ref_decision")
E9 = Fr(1, 10 ** 9)
DP3 = [Fr(-3, 100), Fr(-2, 100), Fr(-2, 100) + E9, Fr(-1, 100), Fr(0), Fr(1, 100), Fr(2, 100) - E9, Fr(2, 100),
       Fr(3, 100), Fr(4, 100), Fr(1, 5)]
SV = [Fr(-1), Fr(1, 5), Fr(1, 5) + E9, Fr(1, 2) - E9, Fr(1, 2), Fr(1)]
CI = [Fr(-1, 100), Fr(0), Fr(1, 1000)]
P1S = [((Fr(0), False), (Fr(0), False)), ((Fr(10), False), (Fr(0), False)), ((Fr(0), False), (Fr(5), False)),
       ((Fr(10), False), (Fr(8), False)), ((Fr(10), False), (Fr(9), False)), ((Fr(10), False), (Fr(10), False)),
       ((Fr(50), True), (Fr(50), True)), ((Fr(50), True), (Fr(40), False))]
DP2 = [Fr(-6, 100), Fr(0), Fr(6, 100) - E9, Fr(6, 100)]
FLAGS = list(itertools.product([False, True], repeat=3))
EXPECTED = {"A": 251_100, "B": 5_699_808_036, "Bstar": 728_388_993_024, "C": 10_749_542_400,
            "D": 17_199_267_840, "E": 18_378_915_840, "F": 52_027_785_216, "G": 2_081_111_408_640,
            "M": 416_222_281_728}


def ref_fold(fl, d, s, ci, p1, dp2):
    V1 = Fr(2, 5); V4 = V1 + d; G = max(d, Fr(2, 100))
    P3 = {"V1": V1, "V4": V4, "V2": V4 - s[0] * G, "rev": V4 - s[1] * G, "lag": V4 - s[2] * G}
    return dict(collapse=fl[0], motion=fl[1], saturated=fl[2], P3=P3, ci_low=ci,
                P1={"V1": p1[0], "V4": p1[1]}, P2={"V1": Fr(1, 2), "V4": Fr(1, 2) + dp2})


def mine(f):
    return {"flags": {"collapse": f["collapse"], "motion": f["motion"], "saturated": f["saturated"]},
            "P3": {"V1": f["P3"]["V1"], "V4": f["P3"]["V4"], "V2": f["P3"]["V2"], "REV": f["P3"]["rev"],
                   "LAG": f["P3"]["lag"]},
            "P2": f["P2"], "P1": f["P1"], "LB": q9(f["ci_low"])}


def signature(f):
    d = f["P3"]["V4"] - f["P3"]["V1"]; b = ref.band(d)
    return (ref.validity(f), b, q9(f["ci_low"]) > 0, ref.sgn(d), ref.c4_fold(f) if b == "pos" else "na",
            ref.c1_fold(f), ref.sgn(f["P1"]["V1"][0] - f["P1"]["V4"][0]),
            q9(f["P2"]["V4"] - f["P2"]["V1"]) >= q9(Fr(6, 100)), ref.sgn(f["P2"]["V4"] - f["P2"]["V1"]))


@pytest.fixture(scope="module")
def grid():
    reps, mult, prim = {}, collections.Counter(), []
    for p in itertools.product(FLAGS, DP3, itertools.product(SV, repeat=3), CI, P1S, DP2):
        f = ref_fold(*p); sig = signature(f)
        mult[sig] += 1; reps.setdefault(sig, f); prim.append(p)
    return reps, mult, prim


@pytest.mark.slow
def test_at12_grid_outcome_counts_and_invariants(grid):
    reps, mult, _ = grid
    assert sum(mult.values()) == 1_824_768 and len(mult) == 1_120
    out = collections.Counter(); viol = 0
    sigs = list(reps)
    mreps = {s: mine(reps[s]) for s in sigs}
    for a in sigs:
        for b in sigs:
            o = dec.decide(mreps[a], mreps[b])
            w = mult[a] * mult[b]
            out[o] += w
            if o != ref.decide(reps[a], reps[b]):
                viol += w
            if o == "A":
                for f in (mreps[a], mreps[b]):
                    if dec.validity(f["flags"]) != "valid" or q9(dec.gain(f)) < Decimal("0.02"):
                        viol += w
                    for c in dec.CONTROLS:
                        m = f["P3"]["V4"] - f["P3"][c]
                        if q9(m) < Decimal("0.02") or q9(m / dec.gain(f)) < Decimal("0.5"):
                            viol += w
            if any(dec.validity(f["flags"]) != "valid" for f in (mreps[a], mreps[b])) and \
                    o not in ("G", "M", "F", "Bstar"):
                viol += w
    assert viol == 0
    assert dict(out) == EXPECTED


@pytest.mark.slow
def test_at12_random_primitive_pairs_equal_reference(grid):
    _, _, prim = grid
    rnd = random.Random(20261003)
    for _ in range(200_000):
        x, y = ref_fold(*rnd.choice(prim)), ref_fold(*rnd.choice(prim))
        assert dec.decide(mine(x), mine(y)) == ref.decide(x, y)


def test_at12_follow_up():
    outs = ["A", "B", "Bstar", "C", "D", "E", "F", "G", "M"]
    for s in itertools.product(outs, repeat=3):
        assert dec.final(*s) == ref.final(*s)
        if dec.final(*s) == "A":
            assert s == ("A", "A", "A")
        if s[0] in ("B", "Bstar"):
            assert dec.final(*s) != "A"


def test_validity_precedence_independent_of_key_order():
    assert dec.validity({"saturated": True, "motion": True, "collapse": True}) == "collapse"
    assert dec.validity({"collapse": False, "saturated": True, "motion": True}) == "motion"


# ---------------- AT-16 ----------------
def test_at16_boundaries():
    assert dec.band(Fr(-2, 100)) == "harm" and dec.band(0) == "null" and dec.band(Fr(2, 100)) == "positive"
    assert dec.band(0.30 - 0.28) == "positive" and q9(0.30 - 0.28) == Decimal("0.020000000")
    assert dec.band(-(0.30 - 0.28)) == "harm"
    assert dec.band(Fr(3, 10) - Fr(7, 25)) == "positive"
    assert q9(0.3 - 0.1) <= dec.S_FAIL                       # S <= 0.2 -> fail
    assert q9(0.7 - 0.2) >= dec.S_PASS                       # S >= 0.5 -> pass if the margin also passes
    assert q9(0.7 + 0.1) <= dec.C1_PASS                      # r <= 0.80 -> pass
    assert not (q9(0.1 + 0.2 - 0.3) > 0)                     # LB_f > 0 is false
    assert q9(1.1 - 1.04) >= dec.C2_MIN                      # dP2 >= 0.06 -> pass
    # raw floats would misclassify every one of these
    assert (0.30 - 0.28) < 0.02 and (0.3 - 0.1) < 0.2 and (0.7 - 0.2) < 0.5 and 0.1 + 0.2 - 0.3 > 0
