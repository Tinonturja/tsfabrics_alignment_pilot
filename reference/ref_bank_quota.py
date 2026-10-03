"""REFERENCE (audit): section-4 water-fill quota rule; reproduces the frozen v1.1 table and the v1.2 A-G4 change."""
def waterfill(total, caps):
    """caps: dict scenario -> capacity, processed in lexicographic order."""
    names = sorted(caps); q = {s: 0 for s in names}; remaining = total
    while remaining > 0:
        open_ = [s for s in names if q[s] < caps[s]]
        if not open_: break
        share, rem = divmod(remaining, len(open_)); given = 0
        for i, s in enumerate(open_):
            add = min(share + (1 if i < rem else 0), caps[s] - q[s]); q[s] += add; given += add
        remaining -= given
        if given == 0: break
    return q
V11 = {'A-G1': {'G2': {'T1_S164_I192_1': 96, 'T1_S164_I193_1': 101}, 'G3': {'T1_S164_I36_1': 91, 'T1_S179_I35_1': 91},
                'G4': {'T1_S478_I118_1': 118, 'T1_S478_I118_2': 133, 'T1_S555_I117_1': 655}},
       'A-G4': {'G1': {'T1_S148_I108_1': 127, 'T1_S148_I108_2': 571, 'T1_S174_I108_1': 7, 'T1_S174_I111_1': 2658},
                'G2': {'T1_S164_I192_1': 96, 'T1_S164_I193_1': 101, 'T1_S164_I199_1': 122}, 'G3': {'T1_S164_I36_1': 91, 'T1_S179_I35_1': 91}}}
FROZEN = {'T1_S164_I192_1': 50, 'T1_S164_I193_1': 50, 'T1_S164_I36_1': 50, 'T1_S179_I35_1': 50, 'T1_S478_I118_1': 34, 'T1_S478_I118_2': 33, 'T1_S555_I117_1': 33}
FROZEN_G4 = {'T1_S148_I108_1': 31, 'T1_S148_I108_2': 31, 'T1_S174_I108_1': 7, 'T1_S174_I111_1': 31, 'T1_S164_I192_1': 34, 'T1_S164_I193_1': 33, 'T1_S164_I199_1': 33, 'T1_S164_I36_1': 50, 'T1_S179_I35_1': 50}
got = {}; [got.update(waterfill(100, c)) for c in V11['A-G1'].values()]; print("v1.1 A-G1 reproduced:", got == FROZEN)
got = {}; [got.update(waterfill(100, c)) for c in V11['A-G4'].values()]; print("v1.1 A-G4 reproduced:", got == FROZEN_G4)
g2 = dict(V11['A-G4']['G2']); del g2['T1_S164_I199_1']
print("v1.2 A-G4 G2 quotas (I199 moved to validation):", waterfill(100, g2))
