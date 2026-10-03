"""AT-14: frozen label files and bank CSV. Needs the dataset's CSV folder (set TSF_ROOT); skipped otherwise.
Only label files are read; no image is opened."""
import numpy as np
import pandas as pd
import pytest

from conftest import CFG, NS, PASSES, SUMMARY
from tsfpilot import config as C
from tsfpilot.bank import build_bank
from tsfpilot.frames import find_root, load_labels

ROOT = find_root()
pytestmark = [pytest.mark.dataset,
              pytest.mark.skipif(ROOT is None, reason="TSFabrics dataset not found (set TSF_ROOT)")]


@pytest.fixture(scope="module")
def labels():
    return {s: load_labels(ROOT, s) for s in SUMMARY.scenario}


def test_label_counts_equal_forensic_table(labels):
    for r in SUMMARY.itertuples():
        lab = labels[r.scenario]
        assert len(lab) == r.n_csv
        assert int((lab == 1).sum()) == r.n_normal, r.scenario
        assert int((lab == 2).sum()) == r.n_cutline_lab, r.scenario
        assert int((lab >= 3).sum()) == r.n_defect, r.scenario


def test_passes_cover_every_test_defect_frame(labels):
    for fold in ("A-G1", "A-G4"):
        for s in CFG["folds"][fold]["test"]:
            lab = labels[s]
            covered = np.zeros(len(lab), bool)
            for p in PASSES[PASSES.scenario == s].itertuples():
                covered[p.pass_start - 1:p.pass_end] = True
                assert int((lab[p.pass_start - 1:p.pass_end] >= 3).sum()) == p.n_defect_frames
            assert not ((lab >= 3) & ~covered).any(), s


def test_bank_capacities_and_quotas(labels):
    t = pd.read_csv(C.repo_path(CFG["data"]["bank_audit_csv"]))
    for fold in ("A-G1", "A-G4"):
        rows = t[t.fold == fold]
        table = {r.scenario: (None if pd.isna(r.margin) else int(r.margin), int(r.spacing)) for r in rows.itertuples()}
        b = build_bank(fold, CFG, labels, table)
        for r in rows.itertuples():
            if r.scenario not in b["capacity"]:          # v1.2: T1_S164_I199_1 is validation in A-G4
                assert fold == "A-G4" and r.scenario == "T1_S164_I199_1"
                continue
            assert b["eligible"][r.scenario] == r.eligible_clean, r.scenario
            assert b["capacity"][r.scenario] == r.capacity, r.scenario
        assert b["quota"] == CFG["folds"][fold]["bank_quota"]
        assert sum(len(v) for v in b["frames"].values()) == 300
        val = CFG["folds"][fold]["validation"]["scenario"]
        assert val not in b["frames"] and not set(b["frames"]) & set(CFG["folds"][fold]["test"])
