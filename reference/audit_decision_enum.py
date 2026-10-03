"""AUDIT: exhaustive enumeration of the v1.2 decision machine over a boundary-value grid,
checked against (1) a closed-form partition written independently from the text and (2) invariants."""
import itertools, collections, random
from fractions import Fraction as Fr
from ref_decision import decide, final, q9, validity, SEV
E9 = Fr(1, 10**9)
DP3 = [Fr(-3,100), Fr(-2,100), Fr(-2,100)+E9, Fr(-1,100), Fr(0), Fr(1,100), Fr(2,100)-E9, Fr(2,100), Fr(3,100), Fr(4,100), Fr(1,5)]
SV  = [Fr(-1), Fr(1,5), Fr(1,5)+E9, Fr(1,2)-E9, Fr(1,2), Fr(1)]
CI  = [Fr(-1,100), Fr(0), Fr(1,1000)]
P1S = [((Fr(0),False),(Fr(0),False)), ((Fr(10),False),(Fr(0),False)), ((Fr(0),False),(Fr(5),False)),
       ((Fr(10),False),(Fr(8),False)), ((Fr(10),False),(Fr(9),False)), ((Fr(10),False),(Fr(10),False)),
       ((Fr(50),True),(Fr(50),True)), ((Fr(50),True),(Fr(40),False))]
DP2 = [Fr(-6,100), Fr(0), Fr(6,100)-E9, Fr(6,100)]
FLAGS = list(itertools.product([False, True], repeat=3))
def fold(fl, d, s, ci, p1, dp2):
    V1 = Fr(2,5); V4 = V1 + d; G = max(d, Fr(2,100))
    P3 = {'V1': V1, 'V4': V4, 'V2': V4 - s[0]*G, 'rev': V4 - s[1]*G, 'lag': V4 - s[2]*G}
    return dict(collapse=fl[0], motion=fl[1], saturated=fl[2], P3=P3, ci_low=ci,
                P1={'V1': p1[0], 'V4': p1[1]}, P2={'V1': Fr(1,2), 'V4': Fr(1,2)+dp2})
# --- independent closed-form partition (written from the text, not from decide()) ---
def predicates(f1, f2):
    F = (f1, f2)
    lab = ['collapse' if f['collapse'] else 'motion' if f['motion'] else 'sat' if f['saturated'] else 'ok' for f in F]
    ninv = sum(l != 'ok' for l in lab)
    d = [q9(f['P3']['V4'] - f['P3']['V1']) for f in F]
    harm = any(x <= q9(Fr(-2,100)) for x in d); bothnull = all(abs(x) < q9(Fr(2,100)) for x in d)
    pos = [x >= q9(Fr(2,100)) for x in d]
    def ctrl(f, c):
        G = f['P3']['V4'] - f['P3']['V1']; m = f['P3']['V4'] - f['P3'][c]
        return q9(m / G), q9(m)
    def c4fail(f): return any(ctrl(f, c)[0] <= q9(Fr(1,5)) for c in ('V2','rev','lag'))
    def c4pass(f): return all(ctrl(f, c)[0] >= q9(Fr(1,2)) and ctrl(f, c)[1] >= q9(Fr(2,100)) for c in ('V2','rev','lag'))
    anyE = any(p and c4fail(f) for p, f in zip(pos, F))
    good = all(pos) and any(q9(f['ci_low']) > 0 for f in F) and all(c4pass(f) for f in F)
    from ref_decision import c1_fold, c7
    good = good and c7(f1, f2) and (all(c1_fold(f) == 'pass' for f in F) or all(q9(f['P2']['V4']-f['P2']['V1']) >= q9(Fr(6,100)) for f in F))
    base = ninv == 0 and not harm and not bothnull and not anyE
    return {'G': ninv == 2 and 'collapse' in lab, 'M': ninv == 2 and 'collapse' not in lab and 'motion' in lab,
            'F': ninv == 2 and 'collapse' not in lab and 'motion' not in lab, 'Bstar': ninv == 1,
            'D': ninv == 0 and harm, 'C': ninv == 0 and not harm and bothnull,
            'E': ninv == 0 and not harm and not bothnull and anyE, 'A': base and good, 'B': base and not good}
# per-fold signature compression: every quantity decide() reads, rounded
def signature(f):
    from ref_decision import band, c4_fold, c1_fold, sgn
    d = f['P3']['V4'] - f['P3']['V1']; b = band(d)
    return (validity(f), b, q9(f['ci_low']) > 0, sgn(d), c4_fold(f) if b == 'pos' else 'na', c1_fold(f),
            sgn(f['P1']['V1'][0] - f['P1']['V4'][0]), q9(f['P2']['V4'] - f['P2']['V1']) >= q9(Fr(6,100)), sgn(f['P2']['V4'] - f['P2']['V1']))
reps = {}; mult = collections.Counter(); nfold = 0
for fl, d, s, ci, p1, dp2 in itertools.product(FLAGS, DP3, itertools.product(SV, repeat=3), CI, P1S, DP2):
    f = fold(fl, d, s, ci, p1, dp2); sig = signature(f); nfold += 1
    mult[sig] += 1; reps.setdefault(sig, f)
print("per-fold primitive states:", nfold, "| distinct per-fold signatures:", len(mult))
sigs = list(reps); out = collections.Counter(); viol = collections.Counter(); total = 0
for a in sigs:
    for b in sigs:
        f1, f2 = reps[a], reps[b]; w = mult[a] * mult[b]; total += w
        o = decide(f1, f2); out[o] += w
        p = predicates(f1, f2)
        if sum(p.values()) != 1: viol['closed-form partition not exactly one true'] += w
        elif not p[o]: viol['chain outcome != closed-form outcome'] += w
        dd = [f['P3']['V4'] - f['P3']['V1'] for f in (f1, f2)]
        if o == 'A':
            if any(q9(x) < q9(Fr(2,100)) for x in dd): viol['A with a fold below +0.02'] += w
            for f in (f1, f2):
                G = f['P3']['V4'] - f['P3']['V1']
                for c in ('V2','rev','lag'):
                    m = f['P3']['V4'] - f['P3'][c]
                    if q9(m) < q9(Fr(2,100)) or q9(m/G) < q9(Fr(1,2)): viol['A with a control within 0.02 or S<0.5'] += w
            if any(validity(f) != 'valid' for f in (f1, f2)): viol['A with invalid fold'] += w
        if any(validity(f) != 'valid' for f in (f1, f2)) and o not in ('G','M','F','Bstar'): viol['invalid fold overridden'] += w
print("total primitive two-fold states:", total)
print("outcome counts:", dict(sorted(out.items())))
print("violations:", dict(viol) if viol else "none")
# random primitive pairs: decide() on raw primitives equals decide() on the signature representatives
rnd = random.Random(5); prim = list(itertools.product(FLAGS, DP3, itertools.product(SV, repeat=3), CI, P1S, DP2)); bad = 0
for _ in range(300000):
    x, y = fold(*rnd.choice(prim)), fold(*rnd.choice(prim))
    bad += decide(x, y) != decide(reps[signature(x)], reps[signature(y)])
print("signature compression check on 300,000 random primitive pairs, mismatches:", bad)
# follow-up
seqs = list(itertools.product(['A','B','Bstar','C','D','E','F','G','M'], repeat=3))
print("follow-up: inconclusive seed 0 ending as A:", sum(final(*s) == 'A' for s in seqs if s[0] in ('B','Bstar')),
      "| A final requires A on all three seeds:", all(final(*s) != 'A' or s == ('A','A','A') for s in seqs))
# floating-point boundary tests
print("float 0.30-0.28 =", 0.30-0.28, "-> q9:", q9(0.30-0.28), ">= 0.02:", q9(0.30-0.28) >= q9(Fr(2,100)))
print("exact Fr(30,100)-Fr(28,100) -> q9:", q9(Fr(30,100)-Fr(28,100)), "| 0.57-0.55 float q9:", q9(0.57-0.55),
      "| 0.1+0.2-0.3 q9:", q9(0.1+0.2-0.3), "| S = 0.01/0.02 float q9:", q9(0.01/0.02), "| 0.7*0.02 vs 0.014:", q9(0.7*0.02) == q9(Fr(14,1000)))
# validity precedence is independent of dict insertion order
f = dict(saturated=True, motion=True, collapse=True); g = dict(collapse=True, motion=True, saturated=True)
print("precedence independent of key order:", validity(f) == validity(g) == 'collapse')
