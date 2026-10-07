"""Stage 1 (section 24): structural and unit validation on synthetic data, reference scripts and frozen CSVs.

Forbidden in Stage 1: any image-derived detector output on any scenario. This script opens no image.
Writes audit/stage1_report.json (pass/fail of every test, AT mapping, hashes) and, if the dataset's label files
are available (TSF_ROOT), audit/bank_frames_v1_2_1.csv (the 300 bank frames per fold, label-derived only).

Usage: python scripts/run_stage1.py [--dataset-root PATH] [--fast]
Result PASS only if every test ran and passed. INCOMPLETE if only the dataset tests (AT-14) were skipped or --fast
was used; INCOMPLETE is never the Stage 1 record. Exit code 0 for PASS, or INCOMPLETE with --allow-no-dataset.
"""
import argparse
import datetime
import glob
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO, "src"))

from tsfpilot import config as C            # noqa: E402
from tsfpilot.manifest import environment, git_state   # noqa: E402

AT_MAP = {
    "test_at05_motion": ["AT-05"],
    "test_at06_to_at10_variants": ["AT-06a", "AT-07", "AT-08", "AT-09", "AT-10"],
    "test_at11_at13_metrics": ["AT-11", "AT-13"],
    "test_at12_at16_decision": ["AT-12", "AT-16"],
    "test_at14_data": ["AT-14"],
    "test_at15_chance": ["AT-15"],
    "test_at17_c6": ["AT-17"],
    "test_bootstrap": ["section 18"],
    "test_passes_bank_config": ["sections 4, 11, 18; config"],
    "test_reference": ["reference self-tests"],
    "test_v122_motion_m1": ["v1.2.2 C1 (M1, not adopted: DL-0017)"],
    "test_v122_calibration_generator": ["v1.2.2 section 4"],
    "test_v122_acceptance": ["v1.2.2 C2 to C4"],
}
NON_BLOCKING = {"test_at17_c6"}           # AT-17 failure: C6 is not reported, Stage 3 is not blocked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset-root", default=None)
    ap.add_argument("--fast", action="store_true", help="skip tests marked slow (not valid for the record)")
    ap.add_argument("--allow-no-dataset", action="store_true")
    a = ap.parse_args()
    if a.dataset_root:
        os.environ["TSF_ROOT"] = a.dataset_root
    os.makedirs(os.path.join(REPO, "audit"), exist_ok=True)
    xml = os.path.join(REPO, "audit", "stage1_junit.xml")
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={xml}", "tests"]
    if a.fast:
        cmd += ["-m", "not slow"]
    t0 = datetime.datetime.now(datetime.timezone.utc)
    proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    print(proc.stdout[-4000:])
    tests = []
    for tc in ET.parse(xml).getroot().iter("testcase"):
        mod = tc.get("classname", "").split(".")[-1]
        status = "passed"
        if tc.find("failure") is not None or tc.find("error") is not None:
            status = "failed"
        elif tc.find("skipped") is not None:
            status = "skipped"
        tests.append({"module": mod, "test": tc.get("name"), "status": status,
                      "seconds": float(tc.get("time", 0)), "covers": AT_MAP.get(mod, [])})
    blocking_fail = [t for t in tests if t["status"] == "failed" and t["module"] not in NON_BLOCKING]
    skipped = [t for t in tests if t["status"] == "skipped"]
    dataset_skips = [t for t in skipped if t["module"] == "test_at14_data"]
    only_dataset_skips = bool(skipped) and len(skipped) == len(dataset_skips)
    if blocking_fail or (skipped and not only_dataset_skips):
        result = "FAIL"
    elif skipped or a.fast:
        result = "INCOMPLETE"                     # never the Stage 1 record: AT-14 (dataset) or slow tests missing
    else:
        result = "PASS"
    ok = result == "PASS" or (result == "INCOMPLETE" and a.allow_no_dataset and not a.fast)
    cfg = C.load()
    globs = ["src/tsfpilot/*.py", "tests/*.py", "tests/fixtures/*.py", "data/frozen/*", "reference/*.py",
             "reference/README.txt", "calibration/c0b/*.py", "calibration/c0b/*.md", "calibration/c0b/*.sha256",
             "calibration/c0b/HASHES.txt", "calibration/c0b/results/*.csv", "calibration/v1_2_2_m1/*", "scripts/*.py",
             "notebooks/*.ipynb"]
    hashed = sorted({p for g in globs for p in glob.glob(os.path.join(REPO, g)) if os.path.isfile(p)} |
                    {os.path.join(REPO, p) for p in ("PREREGISTRATION.md", "PREREGISTRATION_AMENDMENT_v1.2.1.md",
                                                     "docs/stage2/AMENDMENT_v1.2.2_PROTOCOL.md",
                                                     "configs/pilot_v1_2_1.yaml", "configs/pilot_v1_2_2.yaml",
                                                     "requirements.txt", "requirements-stage2.txt", "pyproject.toml")})
    report = {
        "stage": 1, "spec": f"Research Gate v1.2 + v1.2.1{' + v1.2.2' if cfg.get('_version') == 'v1.2.2' else ''}",
        "config_version": cfg.get("_version"), "started_utc": t0.isoformat(),
        "finished_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "result": result, "fast_mode": a.fast,
        "counts": {s: sum(t["status"] == s for t in tests) for s in ("passed", "failed", "skipped")},
        "blocking_failures": [f"{t['module']}::{t['test']}" for t in blocking_fail],
        "c6_reportable": not any(t["status"] == "failed" for t in tests if t["module"] in NON_BLOCKING),
        "dataset_root_found": bool(os.environ.get("TSF_ROOT")) and not dataset_skips,
        "tests": tests, "config_sha256": cfg["_sha256"],
        "hashes": {os.path.relpath(p, REPO): C.file_sha256(p) for p in hashed},
        "files_fingerprint": None,
        "git": git_state(), "environment": environment(),
    }
    report["files_fingerprint"] = hashlib.sha256(
        "".join(f"{k}\t{v}\n" for k, v in sorted(report["hashes"].items())).encode()).hexdigest()
    bank_csv = maybe_write_bank()
    if bank_csv:
        report["bank_frames_csv"] = {"path": os.path.relpath(bank_csv, REPO), "sha256": C.file_sha256(bank_csv)}
    out = os.path.join(REPO, "audit", "stage1_report.json")
    with open(out, "w") as f:
        json.dump(report, f, indent=1)
    print(f"Stage 1 {report['result']}: {report['counts']}  ->  {out}  sha256 {C.file_sha256(out)}")
    sys.exit(0 if ok else 1)


def maybe_write_bank():
    import pandas as pd
    from tsfpilot.bank import build_bank
    from tsfpilot.frames import find_root, load_labels
    root = find_root()
    if root is None:
        return None
    cfg = C.load()
    t = pd.read_csv(C.repo_path(cfg["data"]["bank_audit_csv"]))
    rows = []
    for fold in ("A-G1", "A-G4"):
        scen = sorted({s for g in cfg["folds"][fold]["bank_groups"].values() for s in g})
        labels = {s: load_labels(root, s) for s in scen}
        sub = t[t.fold == fold]
        table = {r.scenario: (None if pd.isna(r.margin) else int(r.margin), int(r.spacing)) for r in sub.itertuples()}
        b = build_bank(fold, cfg, labels, table)
        for group, ss in sorted(cfg["folds"][fold]["bank_groups"].items()):
            for s in sorted(ss):
                for f in b["frames"][s]:
                    rows.append((fold, group, s, f))
    out = os.path.join(REPO, "audit", "bank_frames_v1_2_1.csv")
    pd.DataFrame(rows, columns=["fold", "group", "scenario", "frame"]).to_csv(out, index=False)
    return out


if __name__ == "__main__":
    main()
