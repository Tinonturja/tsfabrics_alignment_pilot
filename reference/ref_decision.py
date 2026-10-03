"""REFERENCE (audit) decision logic for Research Gate v1.2 sections 20-22. Not experiment code.
All inputs that enter comparisons are exact Fractions (metrics) or floats (bootstrap bounds);
every comparison is made on q9(x): the value rounded half-even to 9 decimal places."""
from decimal import Decimal, ROUND_HALF_EVEN, getcontext
from fractions import Fraction as Fr
getcontext().prec = 60
Q = Decimal('1e-9')
def q9(x):
    if isinstance(x, Fr): d = Decimal(x.numerator) / Decimal(x.denominator)
    else: d = Decimal(x)                                   # exact binary value of a float
    return d.quantize(Q, rounding=ROUND_HALF_EVEN)
NB, S_PASS, S_FAIL, C2T, R80, R95 = Decimal('0.02'), Decimal('0.5'), Decimal('0.2'), Decimal('0.06'), Decimal('0.8'), Decimal('0.95')
CONTROLS = ('V2', 'rev', 'lag')
def validity(f):
    """Precedence: collapse > motion > saturated > valid (single ordered chain, independent of dict order)."""
    if f['collapse']: return 'collapse'
    if f['motion']: return 'motion'
    if f['saturated']: return 'saturated'
    return 'valid'
def band(d):
    d = q9(d)
    return 'harm' if d <= -NB else ('pos' if d >= NB else 'null')
def c4_fold(f):
    """Only for folds with band 'pos'. Returns 'pass' | 'between' | 'fail'."""
    G = f['P3']['V4'] - f['P3']['V1']; st = []
    for c in CONTROLS:
        m = f['P3']['V4'] - f['P3'][c]; S = m / G
        if q9(S) <= S_FAIL: st.append('fail')
        elif q9(S) >= S_PASS and q9(m) >= NB: st.append('pass')
        else: st.append('between')
    return 'fail' if 'fail' in st else ('pass' if all(s == 'pass' for s in st) else 'between')
def c1_fold(f):
    a, ca = f['P1']['V1']; b, cb = f['P1']['V4']          # (value capped at 50, censored flag)
    if q9(a) == 0 and q9(b) == 0: return 'nonevaluable'
    if q9(a) == 0: return 'fail'
    if ca and cb: return 'nonevaluable'
    r = q9(b / a)
    return 'pass' if r <= R80 else ('fail' if r > R95 else 'between')
def sgn(x):
    x = q9(x); return (x > 0) - (x < 0)
def c7(f1, f2):
    for key in ('dP3', 'dP2', 'd1'):
        if key == 'd1' and 'nonevaluable' in (c1_fold(f1), c1_fold(f2)): continue
        v = []
        for f in (f1, f2):
            if key == 'dP3': v.append(sgn(f['P3']['V4'] - f['P3']['V1']))
            elif key == 'dP2': v.append(sgn(f['P2']['V4'] - f['P2']['V1']))
            else: v.append(sgn(f['P1']['V1'][0] - f['P1']['V4'][0]))
        if v[0] * v[1] == -1: return False
    return True
def decide(f1, f2):
    F = (f1, f2); val = [validity(f) for f in F]; inv = [v for v in val if v != 'valid']
    if len(inv) == 2:
        if 'collapse' in val: return 'G'
        if 'motion' in val: return 'M'
        return 'F'
    if len(inv) == 1: return 'Bstar'
    b = [band(f['P3']['V4'] - f['P3']['V1']) for f in F]
    if 'harm' in b: return 'D'
    if b == ['null', 'null']: return 'C'
    if any(bb == 'pos' and c4_fold(f) == 'fail' for bb, f in zip(b, F)): return 'E'
    C3 = b == ['pos', 'pos'] and any(q9(f['ci_low']) > 0 for f in F)
    C4 = b == ['pos', 'pos'] and all(c4_fold(f) == 'pass' for f in F)
    C1 = all(c1_fold(f) == 'pass' for f in F)
    C2 = all(q9(f['P2']['V4'] - f['P2']['V1']) >= C2T for f in F)
    return 'A' if (C3 and C4 and c7(f1, f2) and (C1 or C2)) else 'B'
SEV = ['G', 'M', 'F', 'D', 'E', 'C', 'I', 'A']
def final(o0, o1=None, o2=None):
    """Seed follow-up. Seeds 1 and 2 are consulted only if seed 0 is A, B or B*."""
    if o0 not in ('A', 'B', 'Bstar'): return o0
    o = ['I' if x in ('B', 'Bstar') else x for x in (o0, o1, o2)]
    return min(o, key=SEV.index)
