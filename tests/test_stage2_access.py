"""Stage 2 access rules (section 5 rules 1 to 3; section 24). No image is opened: these tests exercise the allow-lists."""
import os
import re

import pytest

from conftest import CFG, REPO
from tsfpilot import access as A
from tsfpilot import config as C


@pytest.fixture(scope="module")
def gate():
    return A.FrameGate("/nonexistent-dataset-root", CFG)


def test_tau_r_scenarios_match_section_4():
    g2 = ["T1_S164_I192_1", "T1_S164_I193_1", "T1_S164_I199_1"]
    g3 = ["T1_S164_I36_1", "T1_S179_I35_1"]
    assert A.tau_r_scenarios(CFG, "A-G1") == sorted(g2 + g3 + CFG["folds"]["A-G4"]["test"])
    assert A.tau_r_scenarios(CFG, "A-G4") == sorted(g2 + g3 + CFG["folds"]["A-G1"]["test"])
    assert "T1_S177_I108_1" in A.tau_r_scenarios(CFG, "A-G4")


def test_bank_record_order_and_size():
    bank = A.load_bank_record(CFG)
    for fold, rows in bank.items():
        assert len(rows) == 300
        assert rows == sorted(rows)                     # groups, then scenarios, then frames ascending
        assert not {s for _, s, _ in rows} & set(CFG["folds"][fold]["test"])


def test_bank_record_hash_is_enforced(tmp_path):
    p = tmp_path / "bank.csv"
    p.write_bytes(open(C.repo_path(A.BANK_RECORD), "rb").read() + b"\n")
    with pytest.raises(ValueError, match="hash"):
        A.load_bank_record(CFG, path=str(p))


def test_bank_frames_only_for_their_own_fold(gate):
    s, f = next(iter(sorted(gate.bank["A-G1"])))
    gate.check("bank", "A-G1", s, f)
    other = [(s2, f2) for s2, f2 in gate.bank["A-G4"] if (s2, f2) not in gate.bank["A-G1"]][0]
    with pytest.raises(A.ForbiddenFrame):
        gate.check("bank", "A-G1", *other)


def test_test_scenario_frames_outside_the_bank_are_refused(gate):
    s = "T1_S555_I117_1"                                  # A-G4 test scenario, A-G1 bank source
    allowed = sorted(f for s2, f in gate.bank["A-G1"] if s2 == s)
    not_in_bank = next(f for f in range(1, 20000) if f not in allowed)
    for purpose, fold in (("bank", "A-G1"), ("validation", "A-G1"), ("bank", "A-G4")):
        with pytest.raises(A.ForbiddenFrame):
            gate.check(purpose, fold, s, not_in_bank)


def test_validation_range(gate):
    gate.check("validation", None, "T1_S164_I199_1", 1)
    gate.check("validation", None, "T1_S164_I199_1", 1212)
    for f in (0, 1213):
        with pytest.raises(A.ForbiddenFrame):
            gate.check("validation", None, "T1_S164_I199_1", f)
    with pytest.raises(A.ForbiddenFrame):
        gate.check("validation", None, "T1_S164_I192_1", 1)


def test_motion_never_reads_the_folds_own_test_group(gate):
    for fold in ("A-G1", "A-G4"):
        for s in CFG["folds"][fold]["test"]:
            with pytest.raises(A.ForbiddenFrame):
                gate.check("motion", fold, s)


def test_motion_frames_cannot_feed_the_detector(gate):
    with pytest.raises(A.ForbiddenFrame):
        gate.batch("motion", "A-G1", [("T1_S164_I192_1", 1)])


def test_labels_only_for_the_validation_scenario(gate):
    with pytest.raises(A.ForbiddenFrame):
        gate.labels("T1_S148_I108_1")


def test_only_the_gate_decodes_images():
    """Structural guard: outside frames.py (the decoder) and access.py (the gate), no pipeline code calls the decoder."""
    pattern = re.compile(r"read_gray\(|cv2\.imread\(")
    offenders = []
    for folder in ("src/tsfpilot", "scripts"):
        for name in sorted(os.listdir(os.path.join(REPO, folder))):
            if not name.endswith(".py") or name in ("frames.py", "access.py"):
                continue
            text = open(os.path.join(REPO, folder, name)).read()
            if pattern.search(text):
                offenders.append(f"{folder}/{name}")
    assert offenders == []
