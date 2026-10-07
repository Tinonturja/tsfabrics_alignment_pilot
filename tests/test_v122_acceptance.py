"""Amendment v1.2.2, section 3 C2 to C4 (AT-04b, AT-03, AT-06b) and the v1.2.2 configuration. No image is opened:
AT-06b runs against a stand-in gate that serves synthetic frames."""
import json
import os

import numpy as np
import pytest

from conftest import CFG, REPO
from tsfpilot import access as A
from tsfpilot import acceptance2 as AT
from tsfpilot import config as C
from tsfpilot import stage2_motion as SM
from tsfpilot.motion import HELD, RELIABLE, UNKNOWN

torch = pytest.importorskip("torch")


def test_configuration_records_the_amendment():
    sa = CFG["stage2_acceptance"]
    assert CFG["_version"] == "v1.2.2" and CFG["motion"]["rule"] == "frozen"
    assert sa["at03_rel"] == AT.AT03_REL and sa["at03_fallback_n"] == AT.AT03_FALLBACK_N
    assert tuple(range(sa["at04b_frames"][0], sa["at04b_frames"][1] + 1)) == AT.AT04_FRAMES
    assert sa["at04b_features_rel"] == AT.AT04B_FEATURES_REL and sa["at04b_maps_rel"] == AT.AT04B_MAPS_REL
    assert tuple(sa["at06b_scenarios"]) == AT.AT06B_SCENARIOS
    assert (sa["at06b_pairs"], sa["at06b_min_holding"]) == (AT.AT06B_PAIRS, AT.AT06B_MIN_HOLDING)
    assert CFG["detector"]["batch_size"] == AT.AT04B_BATCH
    old = C.load(C.repo_path("configs/pilot_v1_2_1.yaml"))
    for sec in old:
        if not sec.startswith("_") and sec not in ("spec", "motion"):
            assert old[sec] == CFG[sec], sec
    assert {k: v for k, v in CFG["motion"].items() if k != "rule"} == old["motion"]


def test_amendment_text_matches_the_constants():
    text = open(os.path.join(REPO, "docs", "stage2", "AMENDMENT_v1.2.2_PROTOCOL.md")).read()
    assert "max|f1 - f4| / max|f4| <= 1e-6" in text and "max|a1 - a4| / max|a4| <= 1e-4" in text
    assert "u = 2^-24, n = 1,026" in text and "1,024 x 2^-53 x d64(q, b*)" in text
    assert "T1_S164_I192_1 and T1_S164_I193_1" in text and "at least 190 of 200" in text
    assert AT.GAMMA == pytest.approx(6.1158e-5, rel=1e-4)


def test_only_the_frozen_motion_rule_runs(tmp_path):
    SM.check_rule(CFG)
    with pytest.raises(ValueError):
        SM.check_rule(dict(CFG, motion=dict(CFG["motion"], rule="M1")))
    bad = tmp_path / "rule.yaml"
    bad.write_text(open(C.DEFAULT).read().replace("  rule: frozen ", "  rule: M1 "))
    with pytest.raises(C.ConfigError):
        C.load(str(bad))


def test_at06b_scenarios_are_training_side_in_both_folds():
    for fold in CFG["folds"]:
        names = A.tau_r_scenarios(CFG, fold)
        for s in AT.AT06B_SCENARIOS:
            assert s in names and s not in CFG["folds"][fold]["test"]


# --- AT-04b (C2) ---

def test_at04b_batches_and_verdict():
    assert AT.batches(AT.AT04_FRAMES, 4) == [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10]]
    rng = np.random.default_rng(0)
    f = rng.normal(size=(10, 50, 8)).astype(np.float32)
    m = {("A-G1", 0): rng.random((10, 4, 5)) + 1, ("A-G4", 0): rng.random((10, 4, 5)) + 1}

    def bump(x, r):
        y = x.copy()
        y.flat[0] += r * np.abs(x).max()
        return y
    assert AT.at04b_verdict(bump(f, 5e-7), f, m, m)["pass"]
    assert not AT.at04b_verdict(bump(f, 2e-6), f, m, m)["pass"]
    m1 = {k: bump(v, 5e-5) for k, v in m.items()}
    assert AT.at04b_verdict(f, f, m1, m)["pass"]
    m1[("A-G4", 0)] = bump(m[("A-G4", 0)], 2e-4)
    rec = AT.at04b_verdict(f, f, m1, m)
    assert not rec["pass"] and rec["rel_maps"]["A-G4 seed 0"] > 1e-4


# --- AT-03 (C3) ---

def test_smallest_index_argmin():
    d = torch.tensor([3.0, 1.0, 2.0, 1.0], dtype=torch.float64)
    assert AT.smallest_index_argmin(d) == 1


def test_fallback_bound_by_hand():
    q = torch.tensor([[1.0, -2.0]], dtype=torch.float64)
    b = torch.tensor([[2.0, 1.0], [0.0, 0.0]], dtype=torch.float64)
    d64 = torch.tensor([5.0], dtype=torch.float64)                 # |q - 0|^2 = 5 (b* = index 1)
    e_star = AT.GAMMA * (5 + 0 + 0) + AT.F64_TERM * 5
    e_hat = AT.GAMMA * (5 + 5 + 2 * (2 + 2)) + AT.F64_TERM * 5
    got = AT.at03_fallback_bound(q, b, torch.tensor([1]), torch.tensor([0]), d64)
    assert float(got[0]) == pytest.approx(max(e_star, e_hat), rel=1e-12)


def _features_and_coreset(scale, seed=1):
    from tsfpilot.scoring import Coreset
    g = torch.Generator().manual_seed(seed)
    base = torch.randn(64, 1024, generator=g, dtype=torch.float64) * scale
    q = (base[torch.arange(8000) % 64] + 0.01 * torch.randn(8000, 1024, generator=g, dtype=torch.float64)).float()
    cs = (base.repeat(4, 1) + 0.01 * torch.randn(256, 1024, generator=g, dtype=torch.float64)).float()
    return q, Coreset(cs, torch.device("cpu"))


def test_at03_primary_passes_on_moderate_norms():
    q, cs = _features_and_coreset(0.05)
    rec = AT.at03(q, cs, "A-G1")
    assert rec["primary_pass"] and rec["pass"] and not rec["fallback"]["applied"]


def test_at03_fallback_decides_when_cancellation_dominates():
    q, cs = _features_and_coreset(3.0)          # ||q||^2 about 9,000 against distances about 0.2
    rec = AT.at03(q, cs, "A-G1")
    assert not rec["primary_pass"] and rec["fallback"]["applied"]
    assert rec["fallback"]["pass"] and rec["pass"] and rec["fallback"]["max_err_over_bound"] < 1


# --- AT-06b (C4) ---

def statuses(n, reliable):
    st = np.full(n, UNKNOWN, np.int8)
    st[reliable] = RELIABLE
    return st


def test_selection_rules():
    a, b = AT.AT06B_SCENARIOS
    st = statuses(600, np.arange(1, 600))
    st[50] = HELD
    sel, rule = AT.at06b_select([(a, st), (b, statuses(600, []))])
    assert rule == f"consecutive run in {a}" and sel[0] == (a, 52) and sel[-1] == (a, 251) and len(sel) == 200
    sel, rule = AT.at06b_select([(a, statuses(600, np.arange(1, 150))), (b, statuses(600, np.arange(10, 300)))])
    assert rule == f"consecutive run in {b}" and sel[0] == (b, 11) and len(sel) == 200
    # 150 at the end of I192 and 60 at the start of I193: no run crosses scenarios, so rule 3 applies
    sel, rule = AT.at06b_select([(a, statuses(400, np.arange(250, 400))), (b, statuses(400, np.arange(0, 60)))])
    assert rule.startswith("first reliable") and sel[0] == (a, 251) and sel[149] == (a, 400)
    assert sel[150] == (b, 1) and sel[-1] == (b, 50)
    sel, rule = AT.at06b_select([(a, statuses(300, np.arange(0, 300, 2))), (b, statuses(100, [3]))])
    assert sel is None and rule.startswith("only 151")


class StandInGate:
    """Serves frames of a smooth texture moving dx px per frame; records when each read happened."""

    def __init__(self, dx, n, out_dir, fold):
        rng = np.random.default_rng(4)
        width = 800 + abs(dx) * n + 16
        tex = rng.random((640, width)).astype(np.float32)
        k = np.ones(9, np.float32) / 9
        self.tex = np.apply_along_axis(lambda r: np.convolve(r, k, "same"), 1, tex)
        self.dx, self.out_dir, self.fold, self.reads = dx, out_dir, fold, []

    def motion_image(self, fold, scenario, frame):
        assert fold == self.fold
        assert os.path.exists(os.path.join(self.out_dir, f"at06b_selection_{fold}.json")), "read before selection"
        self.reads.append((scenario, frame))
        a = -self.dx * (frame - 1)                       # I_t(x) = I_(t-1)(x - dx), dx < 0
        return (255 * self.tex[:, a:a + 800]).astype(np.uint8)


def raw_for(dx, n):
    d = np.full(n, float(dx))
    has = np.ones(n, bool)
    has[0] = False
    return d, np.zeros(n), np.ones(n), has


def test_at06b_end_to_end_on_moving_texture(tmp_path):
    a, b = AT.AT06B_SCENARIOS
    gate = StandInGate(-86, 210, str(tmp_path), "A-G1")
    raw = {a: raw_for(-86, 210), b: raw_for(-86, 210)}
    rec = AT.at06b(gate, raw, "A-G1", 0.0, CFG["motion"], str(tmp_path))
    sel = json.load(open(tmp_path / "at06b_selection_A-G1.json"))
    assert rec["pass"] and rec["holding"] == 200 and rec["rule"] == f"consecutive run in {a}"
    assert sel["pairs"][0] == [a, 2, 11] and sel["pairs"][-1] == [a, 201, 11]      # floor(86 / 8 + 0.5) = 11
    assert {s for s, _ in gate.reads} == {a} and min(f for _, f in gate.reads) == 1
    assert all(r[5] > r[3] for r in rec["pairs"])                                   # zero shift is worse than U
    assert rec["selection_sha256"] == C.file_sha256(str(tmp_path / "at06b_selection_A-G1.json"))


def test_at06b_wrong_sign_fails(tmp_path):
    a, b = AT.AT06B_SCENARIOS
    gate = StandInGate(-86, 210, str(tmp_path), "A-G4")
    raw = {a: raw_for(86, 210), b: raw_for(86, 210)}                 # estimates with the wrong sign
    rec = AT.at06b(gate, raw, "A-G4", 0.0, CFG["motion"], str(tmp_path))
    assert not rec["pass"] and rec["holding"] < 10


def test_at06b_not_applicable_or_failing_reads_nothing(tmp_path):
    a, b = AT.AT06B_SCENARIOS
    gate = StandInGate(-86, 20, str(tmp_path), "A-G1")
    rec = AT.at06b(gate, {}, "A-G1", None, CFG["motion"], str(tmp_path))
    assert rec["applicable"] is False and rec["pass"] is None
    raw = {a: raw_for(-86, 120), b: raw_for(-86, 60)}                  # 119 + 59 reliable frames: fewer than 200
    rec = AT.at06b(gate, raw, "A-G1", 0.0, CFG["motion"], str(tmp_path))
    assert rec["pass"] is False and gate.reads == [] and rec["rule"].startswith("only 178")


def test_motion_image_is_gated_and_logged(monkeypatch):
    gate = A.FrameGate("/nonexistent-dataset-root", CFG)
    monkeypatch.setattr(A, "image_paths", lambda root, s: [f"{s}/{i}.png" for i in range(1, 2000)])
    monkeypatch.setattr(A, "read_gray", lambda p: np.zeros((640, 800), np.uint8))
    img = gate.motion_image("A-G1", AT.AT06B_SCENARIOS[0], 5)
    assert isinstance(img, np.ndarray) and not isinstance(img, A.FrameBatch)
    assert gate.audit_reads() == []
    assert {"purpose": "motion", "fold": "A-G1", "scenario": AT.AT06B_SCENARIOS[0], "frames_read": 1} in \
        gate.read_summary()
    for fold in CFG["folds"]:
        for s in CFG["folds"][fold]["test"]:
            with pytest.raises(A.ForbiddenFrame):
                gate.motion_image(fold, s, 5)
