"""Section 4 (bank rule), section 11 (windows, N_f, carry-over), section 18 (units), config integrity."""
import os

import numpy as np
import pandas as pd
import pytest

from conftest import CFG, REPO
from tsfpilot import config as C
from tsfpilot.bank import capacity_list, eligible, select, waterfill
from tsfpilot.passes import phase_units, window_end


@pytest.mark.parametrize("fold", ["A-G1", "A-G4"])
def test_fold_units_match_spec(layouts, fold):
    L = layouts[fold]
    exp = CFG["folds"][fold]["expected"]
    assert (L.n, L.n_passes, L.n_tracks) == (exp["frames"], exp["passes"], exp["tracks"])
    assert L.n_B == {"A-G1": 39, "A-G4": 22}[fold]
    assert L.n_P == {"A-G1": 18, "A-G4": 32}[fold]
    # section 11 estimate with scenario-median k: 24 of 162 and 10 of 99 carry-over-affected passes
    assert int(L.carry.sum()) == {"A-G1": 24, "A-G4": 10}[fold]
    # windows are disjoint, start at s_p, and no window frame is in N_f
    w = np.zeros(L.n, int)
    for a, b in zip(L.w_lo, L.w_hi):
        w[a:b + 1] += 1
    assert w.max() == 1 and not (L.isN & (w > 0)).any()
    assert np.array_equal(L.w_lo, L.s_glob) and (L.w_hi >= L.e_glob).all()
    assert L.nN == {"A-G1": 41800, "A-G4": 20964}[fold]
    assert L.nN_P.sum() == L.nN and L.nN_B.sum() == L.nN


def test_window_end_rule():
    K = np.full(100, 7)
    assert window_end(10, 15, 100, K, 60) == 21                     # g = e + K - 1
    assert window_end(10, 15, 100, K, 16) == 15                     # adjacent pass: no grace
    assert window_end(10, 15, 18, K, 19) == 18                      # capped at N_s
    assert window_end(10, 15, 100, np.full(100, 25), 99) == 39      # g <= e + 24
    assert window_end(10, 15, 100, K, 60, grace=False) == 15        # sensitivity S1


def test_phase_units_rules():
    lab = np.ones(400, int)
    for a in (50, 60, 210):                                          # anchors at 50 and 210; 60 is skipped (2*10 < P)
        lab[a - 1:a + 2] = 2
    bins, acc = phase_units(lab, 150, (2, 5), 50)
    assert acc == [50, 210]
    t = np.arange(1, 401)
    phi = np.where(t < 50, (t - 50) % 150, np.where(t < 210, (t - 50) % 150, (t - 210) % 150))
    assert np.array_equal(bins, phi // 50)
    b2, a2 = phase_units(np.ones(100, int), 59, (2, 5), 50)
    assert a2 == [] and np.array_equal(b2, ((np.arange(1, 101) - 1) % 59) // 50)


def test_bank_rule_reproduces_frozen_quotas():
    t = pd.read_csv(C.repo_path(CFG["data"]["bank_audit_csv"]))
    for fold in ("A-G1", "A-G4"):
        got = {}
        for group, scen in CFG["folds"][fold]["bank_groups"].items():
            caps = {s: int(t[(t.fold == fold) & (t.scenario == s)].capacity.iloc[0]) for s in scen}
            got.update(waterfill(CFG["bank"]["per_group_total"], caps))
        assert got == CFG["folds"][fold]["bank_quota"]
        assert sum(got.values()) == CFG["bank"]["frames_per_fold"]


def test_bank_eligibility_capacity_and_selection():
    lab = np.ones(60, int); lab[29] = 4                              # defect at frame 30
    e = eligible(lab, [30], margin=5)
    assert 25 not in e and 24 in e and 35 not in e and 36 in e       # |f - d| > margin, strict
    assert capacity_list([1, 2, 5, 9, 10, 20], 4) == [1, 5, 9, 20]
    C_ = list(range(100, 200))
    assert select(C_, 4) == [C_[12], C_[37], C_[62], C_[87]]         # floor((j + 0.5) c / q)


def test_code_constants_equal_config():
    """Constants written in code must equal the frozen YAML, so an edited config cannot silently diverge."""
    from decimal import Decimal
    from tsfpilot import decision, events
    cr, m, e = CFG["criteria"], CFG["metrics"], CFG["events"]
    assert decision.BAND == Decimal(cr["band"]) and decision.C1_PASS == Decimal(cr["c1_pass"])
    assert decision.C1_FAIL == Decimal(cr["c1_fail"]) and decision.C2_MIN == Decimal(cr["c2_min"])
    assert decision.S_PASS == Decimal(cr["c4_pass_share"]) and decision.S_FAIL == Decimal(cr["c4_fail_share"])
    assert (cr["c0a_num"], cr["c0a_den"]) == (19, 20)                # metrics.c0a_saturated: 20 x det >= 19 x n
    assert events.GAP == e["merge_gap"] and events.CAP == e["duration_cap"] and e["fa_per"] == 1000
    assert (m["p1_recall_num"], m["p1_recall_den"], m["p1_cap"], m["p2_fa"], m["p3_fmax"]) == (4, 5, 50, 2, 10)
    assert CFG["motion"]["cell_px"] == 8 and CFG["motion"]["tau_r_min_consistent"] == 0.95
    assert CFG["chance"]["n_shifts"] == 200 and CFG["chance"]["collapse_k"] == 10


def test_config_integrity(tmp_path):
    assert CFG["spec"]["preregistration_sha256"] == C.file_sha256(os.path.join(REPO, "PREREGISTRATION.md"))
    assert CFG["spec"]["amendment_v1_2_1_sha256"] == C.file_sha256(
        os.path.join(REPO, "PREREGISTRATION_AMENDMENT_v1.2.1.md"))
    assert CFG["_version"] == "v1.2.2" and CFG["spec"]["amendment_v1_2_2_sha256"] == C.file_sha256(
        os.path.join(REPO, "docs", "stage2", "AMENDMENT_v1.2.2_PROTOCOL.md"))
    bad = tmp_path / "bad.yaml"
    bad.write_text(open(C.DEFAULT).read().replace("  merge_gap: 2\n", "  merge_gap: 2\n  surprise: 1\n"))
    with pytest.raises(C.ConfigError):
        C.load(str(bad))
    bad.write_text(open(C.DEFAULT).read().replace("offset_support: full_cyclic_group", "offset_support: band"))
    with pytest.raises(C.ConfigError):
        C.load(str(bad))
    for s, P in CFG["periods"].items():
        assert isinstance(P, int) and P > 0
