"""Stage 2 data access (section 5 rules 1 to 3; section 24, Stage 2 "Data allowed" and "Forbidden").

Every image Stage 2 reads goes through FrameGate, and every request names its purpose:

  bank        the 300 (scenario, frame) pairs per fold of the Stage 1 bank record (DL-0012). Features only:
              these frames are never scored, displayed or summarised.
  validation  T1_S164_I199_1, frames 1 to 1,212. The only frames that may be scored in Stage 2.
  motion      every frame of the training-side scenarios used for tau_r. Phase correlation only.

Anything outside these lists raises ForbiddenFrame. Labels can be read for the validation scenario only.
The gate keeps a log of what was read, which the Stage 2 report checks against the allow-lists.
"""
from collections import Counter
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import config as C
from .frames import image_paths, load_labels, read_gray

BANK_RECORD = "audit/stage1_kaggle/bank_frames_v1_2_1.csv"
BANK_RECORD_SHA256 = "534535eb8ea947bed4fb9c9a03352f52ba0ba197ba7694385b5735e9b936a535"   # DL-0012
PURPOSES = ("bank", "validation", "motion")


class ForbiddenFrame(RuntimeError):
    pass


@dataclass(frozen=True)
class FrameBatch:
    """Decoded frames plus where they came from. `purpose` travels with the pixels so that the scorer can refuse
    anything that is not a validation frame."""
    purpose: str
    fold: str
    keys: tuple             # ((scenario, frame), ...), frames 1-based
    images: np.ndarray      # uint8 (B, 640, 800)


def group_of(clusters):
    return dict(zip(clusters.scenario, clusters.condition_group))


def test_group(cfg, fold):
    groups = {group_of(load_clusters(cfg))[s] for s in cfg["folds"][fold]["test"]}
    if len(groups) != 1:
        raise ValueError(f"{fold}: test scenarios span groups {sorted(groups)}")
    return groups.pop()


def load_clusters(cfg):
    return pd.read_csv(C.repo_path(cfg["data"]["clusters_csv"]))


def tau_r_scenarios(cfg, fold):
    """Section 4: every scenario of the fold's training-side groups, full length, label-free."""
    groups = group_of(load_clusters(cfg))
    wanted = set(cfg["folds"][fold]["tau_r_groups"])
    out = sorted(s for s, g in groups.items() if g in wanted)
    own = set(cfg["folds"][fold]["test"])
    if own & set(out) or test_group(cfg, fold) in wanted:
        raise ForbiddenFrame(f"{fold}: tau_r would use the fold's own test group")
    return out


def load_bank_record(cfg, path=None, expected_sha256=BANK_RECORD_SHA256):
    """The Stage 1 bank record, checked against its recorded hash, the config quotas and the fold structure.
    Returns {fold: [(group, scenario, frame), ...]} in the section 6 coreset input order:
    groups ascending, scenarios lexicographic, frames ascending."""
    path = path or C.repo_path(BANK_RECORD)
    got = C.file_sha256(path)
    if got != expected_sha256:
        raise ValueError(f"bank record hash {got} differs from the Stage 1 record {expected_sha256}")
    df = pd.read_csv(path)
    groups = group_of(load_clusters(cfg))
    val = cfg["folds"]["A-G1"]["validation"]["scenario"]
    out = {}
    for fold, fc in cfg["folds"].items():
        d = df[df.fold == fold]
        quota = d.groupby("scenario").size().to_dict()
        expected = {s: q for s, q in fc["bank_quota"].items() if q > 0}
        if quota != expected:
            raise ValueError(f"{fold}: bank quotas {quota} differ from the config {expected}")
        if set(d.scenario) & set(fc["test"]) or val in set(d.scenario):
            raise ForbiddenFrame(f"{fold}: bank overlaps the fold's test set or the validation scenario")
        for r in d.itertuples():
            if groups[r.scenario] != r.group:
                raise ValueError(f"{r.scenario}: group {r.group} differs from the clusters CSV")
        rows = sorted((r.group, r.scenario, int(r.frame)) for r in d.itertuples())
        if len(rows) != cfg["bank"]["frames_per_fold"] or len(set(rows)) != len(rows):
            raise ValueError(f"{fold}: expected {cfg['bank']['frames_per_fold']} distinct bank frames")
        out[fold] = rows
    return out


def check_validation_role(cfg):
    """Section 4 and section 5 rule 5: the validation scenario is a test scenario nowhere and a bank source nowhere."""
    vals = {(f["validation"]["scenario"], f["validation"]["first"], f["validation"]["last"])
            for f in cfg["folds"].values()}
    if len(vals) != 1:
        raise ValueError(f"folds disagree on validation: {sorted(vals)}")
    scen, first, last = vals.pop()
    for fold, fc in cfg["folds"].items():
        if scen in fc["test"] or fc["bank_quota"].get(scen, 0) > 0:
            raise ForbiddenFrame(f"{fold}: validation scenario {scen} is a test or bank scenario")
    return scen, first, last


class FrameGate:
    def __init__(self, root, cfg, bank_record=None):
        self.root = root
        self.cfg = cfg
        self.val_scenario, first, last = check_validation_role(cfg)
        self.val_frames = range(first, last + 1)
        bank = bank_record if bank_record is not None else load_bank_record(cfg)
        self.bank = {fold: {(s, f) for _, s, f in rows} for fold, rows in bank.items()}
        self.motion = {fold: set(tau_r_scenarios(cfg, fold)) for fold in cfg["folds"]}
        self._paths = {}
        self.read_log = Counter()        # (purpose, fold, scenario) -> frames read
        self._read_keys = set()          # (purpose, fold, scenario, frame) for detector inputs

    def check(self, purpose, fold, scenario, frame=None):
        if purpose == "bank":
            ok = (scenario, frame) in self.bank.get(fold, ())
        elif purpose == "validation":
            ok = scenario == self.val_scenario and frame in self.val_frames
        elif purpose == "motion":
            ok = scenario in self.motion.get(fold, ())
        else:
            raise ValueError(f"unknown purpose {purpose!r}")
        if not ok:
            raise ForbiddenFrame(f"{purpose} access to {scenario} frame {frame} (fold {fold}) is not allowed")

    def _path(self, scenario, frame):
        if scenario not in self._paths:
            self._paths[scenario] = image_paths(self.root, scenario)
        return self._paths[scenario][frame - 1]

    def batch(self, purpose, fold, keys):
        """Decode a list of (scenario, frame) for the detector. Only 'bank' and 'validation' are detector purposes."""
        if purpose not in ("bank", "validation"):
            raise ForbiddenFrame(f"purpose {purpose!r} cannot feed the detector")
        keys = tuple((s, int(f)) for s, f in keys)
        for s, f in keys:
            self.check(purpose, fold, s, f)
        imgs = np.stack([read_gray(self._path(s, f)) for s, f in keys])
        for s, f in keys:
            self.read_log[(purpose, fold, s)] += 1
            self._read_keys.add((purpose, fold, s, f))
        return FrameBatch(purpose, fold, keys, imgs)

    def motion_frames(self, fold, scenario):
        """All frames of one tau_r scenario in order, for phase correlation."""
        self.check("motion", fold, scenario)
        paths = image_paths(self.root, scenario)
        for p in paths:
            self.read_log[("motion", fold, scenario)] += 1
            yield read_gray(p)

    def validation_image(self, frame):
        """One validation frame as uint8, for AT-06b (motion and images of the validation scenario)."""
        self.check("validation", None, self.val_scenario, frame)
        self.read_log[("validation", None, self.val_scenario)] += 1
        self._read_keys.add(("validation", None, self.val_scenario, frame))
        return read_gray(self._path(self.val_scenario, frame))

    def validation_labels(self):
        return load_labels(self.root, self.val_scenario)

    def labels(self, scenario):
        if scenario != self.val_scenario:
            raise ForbiddenFrame(f"Stage 2 reads no labels except the validation scenario's ({scenario} requested)")
        return self.validation_labels()

    def audit_reads(self):
        """Re-check every logged read against the allow-lists. Returns the list of violations (empty if clean)."""
        bad = []
        for purpose, fold, s, f in sorted(self._read_keys, key=str):
            try:
                self.check(purpose, fold, s, f)
            except ForbiddenFrame as e:
                bad.append(str(e))
        for (purpose, fold, s), _ in self.read_log.items():
            if purpose == "motion":
                try:
                    self.check(purpose, fold, s)
                except ForbiddenFrame as e:
                    bad.append(str(e))
        return bad

    def read_summary(self):
        return [{"purpose": p, "fold": f, "scenario": s, "frames_read": n}
                for (p, f, s), n in sorted(self.read_log.items(), key=str)]
