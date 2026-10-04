"""Stage 2 (section 24): detector, coresets, validation constants, tau_r, and AT-01 to AT-04b plus AT-06b.

Allowed data: bank frames of both folds, validation frames (T1_S164_I199_1, frames 1 to 1,212), and motion on the
training-side scenarios of each fold. No test-scenario frame is scored; src/tsfpilot/access.py enforces this.

Phases. Each writes phase_<X>.json into --out; a finished phase is skipped on rerun; the run stops at the first
phase whose acceptance test fails.
  0  CPU  Stage 2 unit tests (pytest) as a pre-flight
  A  CPU  raw motion on every tau_r scenario; tau_r per fold; validation statuses; AT-06b
  B  GPU  layer-by-layer trace; AT-02 against the official PatchCore._embed on validation frames 1 to 5
  C  GPU  bank features per fold; coresets for seeds 0, 1, 2; seed 0 rebuilt once as a reproducibility check
  D  GPU  validation maps for all six coresets in one pass; AT-01, AT-03, AT-04a, AT-04b
  E  CPU  mu0, b1, b3, tau_cell, b1 profile, deployment thresholds; frozen manifest; requirements.lock

Usage:
  python scripts/run_stage2.py --dataset-root PATH --out OUT [--work TMP] [--workers 2] [--smoke]
--smoke caps every data size so the chain runs in minutes. A smoke report is never the Stage 2 record.
"""
import argparse
import datetime
import glob
import hashlib
import json
import os
import subprocess
import sys
import time

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO, "src"))

import numpy as np                                            # noqa: E402

from tsfpilot import access                                   # noqa: E402
from tsfpilot import config as C                              # noqa: E402
from tsfpilot import stage2_motion as SM                      # noqa: E402
from tsfpilot.frames import find_root                         # noqa: E402
from tsfpilot.manifest import environment, git_state          # noqa: E402

STAGE1_REPORT = "audit/stage1_kaggle/stage1_report.json"
STAGE1_REPORT_SHA256 = "41ca8d47daa5b96cdfba15c963d1b86988c071591af6c98850c4e3c229c9d911"   # DL-0012
SMOKE = {"bank_frames": 4, "validation_last": 12, "motion_frames": 60}
HASHED = ["src/tsfpilot/*.py", "scripts/*.py", "tests/*.py", "tests/fixtures/*.py", "notebooks/*.ipynb",
          "third_party/patchcore/*", "third_party/patchcore/patchcore/*.py", "data/frozen/*", "configs/*.yaml",
          "docs/stage2/*.md", "PREREGISTRATION.md", "PREREGISTRATION_AMENDMENT_v1.2.1.md", "requirements.txt",
          "pyproject.toml", "audit/stage1_kaggle/bank_frames_v1_2_1.csv"]


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _plain(x):
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.floating):
        return float(x)
    if isinstance(x, (np.ndarray, tuple)):
        return list(x)
    if isinstance(x, np.bool_):
        return bool(x)
    raise TypeError(type(x))


def dump(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, sort_keys=True, default=_plain)


def source_hashes():
    files = sorted({p for g in HASHED for p in glob.glob(os.path.join(REPO, g)) if os.path.isfile(p)})
    hashes = {os.path.relpath(p, REPO): C.file_sha256(p) for p in files}
    fingerprint = hashlib.sha256("".join(f"{k}\t{v}\n" for k, v in sorted(hashes.items())).encode()).hexdigest()
    return hashes, fingerprint


def preconditions(cfg):
    """Frozen inputs must verify before any image is read."""
    rec = {"config_sha256": cfg["_sha256"],
           "preregistration_sha256": C.file_sha256(C.repo_path("PREREGISTRATION.md")),
           "amendment_sha256": C.file_sha256(C.repo_path("PREREGISTRATION_AMENDMENT_v1.2.1.md")),
           "git": git_state(), "problems": []}
    if rec["preregistration_sha256"] != cfg["spec"]["preregistration_sha256"]:
        rec["problems"].append("PREREGISTRATION.md hash differs from the config")
    if rec["amendment_sha256"] != cfg["spec"]["amendment_v1_2_1_sha256"]:
        rec["problems"].append("amendment hash differs from the config")
    try:
        access.load_bank_record(cfg)
        rec["bank_record_sha256"] = access.BANK_RECORD_SHA256
    except Exception as e:                                    # noqa: BLE001 - recorded, then the run stops
        rec["problems"].append(f"bank record: {e}")
    s1 = C.repo_path(STAGE1_REPORT)
    if not os.path.exists(s1):
        rec["problems"].append(f"{STAGE1_REPORT} is missing")
    else:
        rec["stage1_report_sha256"] = C.file_sha256(s1)
        if rec["stage1_report_sha256"] != STAGE1_REPORT_SHA256 or json.load(open(s1)).get("result") != "PASS":
            rec["problems"].append("the Stage 1 record does not verify (hash or result)")
    return rec


def phase_0(ctx):
    xml = os.path.join(ctx["out"], "stage2_unit_tests.xml")
    tests = sorted(glob.glob(os.path.join(REPO, "tests", "test_stage2_*.py"))) + \
        [os.path.join(REPO, "tests", "test_third_party_pin.py")]
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={xml}",
                           *tests], cwd=REPO, capture_output=True, text=True)
    tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    ok = proc.returncode == 0 and "skipped" not in tail
    return {"phase": "0", "pytest_summary": tail, "pass": ok}


def phase_a(ctx):
    from tsfpilot import acceptance2 as AT
    cfg, gate = ctx["cfg"], access.FrameGate(ctx["root"], ctx["cfg"])
    mdir = os.path.join(ctx["out"], "motion")
    limit = SMOKE["motion_frames"] if ctx["smoke"] else None
    raw, reads = SM.raw_motion(ctx["root"], cfg, mdir, ctx["workers"], limit)
    folds = {}
    for fold in sorted(cfg["folds"]):
        tr = SM.tau_r_record(raw, cfg, fold)
        vm = SM.scenario_motion(raw[gate.val_scenario], tr["tau_r"], cfg)
        np.savez(os.path.join(mdir, f"validation_motion_{fold}.npz"), **vm)
        counts = {name: int(np.sum(vm["status"] == code)) for name, code in
                  (("reliable", 2), ("held", 1), ("unknown", 0))}
        folds[fold] = {"tau_r": tr, "validation_status_counts": counts,
                       "AT-06b": AT.at06b(gate, vm, fold, tr["tau_r"])}
    applicable = [f["AT-06b"]["pass"] for f in folds.values() if f["AT-06b"]["applicable"]]
    return {"phase": "A", "folds": folds, "frames_without_estimate": SM.frames_without_estimate(raw),
            "motion_files": {os.path.basename(p): C.file_sha256(p) for p in sorted(glob.glob(mdir + "/*.npz"))},
            "reads": reads + gate.read_summary(), "read_violations": gate.audit_reads(),
            "pass": all(applicable) and not gate.audit_reads()}


def phase_b(ctx, net):
    import torch
    from tsfpilot import acceptance2 as AT
    from tsfpilot import detector as D
    cfg, dcfg, dev = ctx["cfg"], ctx["cfg"]["detector"], ctx["device"]
    gate = access.FrameGate(ctx["root"], cfg)
    img = gate.batch("validation", None, [(gate.val_scenario, 1)]).images[0]
    trace, _, _, _ = D.shape_trace(net, img, dcfg, dev)
    ref_net = D.load_backbone(dev)                       # the official hooks attach to this copy only
    at02 = AT.at02(net, AT.official_patchcore(ref_net, dev), gate, dcfg, dev)
    del ref_net
    torch.cuda.empty_cache()
    return {"phase": "B", "trace": [[k, list(v)] for k, v in trace], "AT-02": at02,
            "reads": gate.read_summary(), "read_violations": gate.audit_reads(),
            "pass": at02["pass"] and not gate.audit_reads()}


def phase_c(ctx, net):
    import torch
    from tsfpilot import coreset as CS
    cfg, dcfg, dev = ctx["cfg"], ctx["cfg"]["detector"], ctx["device"]
    gate = access.FrameGate(ctx["root"], cfg)
    bank = access.load_bank_record(cfg)
    records, checks = [], {}
    for fold in sorted(cfg["folds"]):
        rows = bank[fold][:SMOKE["bank_frames"]] if ctx["smoke"] else bank[fold]
        path = os.path.join(ctx["work"], f"bank_features_{fold}.npy")
        t0 = time.time()
        feats = CS.write_bank_features(gate, net, fold, rows, dcfg, dev, path)
        t_feat = time.time() - t0
        meta = {"method": "official ApproximateGreedyCoresetSampler (fcaa92f), projection in row chunks (D5)",
                "percentage": dcfg["coreset_percentage"], "starting_points": dcfg["coreset_starting_points"],
                "projection_dim": dcfg["coreset_projection_dim"], "chunk_rows": dcfg["coreset_chunk_rows"],
                "candidates": int(feats.shape[0]), "candidate_dim": int(feats.shape[1]),
                "source_frames": [[g, s, f] for g, s, f in rows],
                "input_order": "groups ascending, scenarios lexicographic, frames ascending, cells row-major",
                "bank_record_sha256": access.BANK_RECORD_SHA256, "feature_seconds": round(t_feat, 1)}
        first = None
        for seed in dcfg["coreset_seeds"]:
            t0 = time.time()
            idx, vec = CS.build(feats, seed, dcfg, dev)
            rec = CS.save(ctx["frozen"], fold, seed, idx, vec, dict(meta, coreset_seconds=round(time.time() - t0, 1)))
            records.append({k: v for k, v in rec.items() if k != "source_frames"})
            if seed == dcfg["coreset_seeds"][0]:
                first = idx
        again, _ = CS.build(feats, dcfg["coreset_seeds"][0], dcfg, dev)
        checks[fold] = bool(np.array_equal(first, again))
        del feats
        os.remove(path)                                      # bank features are never kept (section 24)
        torch.cuda.empty_cache()
    return {"phase": "C", "coresets": records, "seed0_rebuild_identical": checks,
            "reads": gate.read_summary(), "read_violations": gate.audit_reads(),
            "pass": all(checks.values()) and not gate.audit_reads()}


def phase_d(ctx, net, trace):
    import torch
    from tsfpilot import acceptance2 as AT
    from tsfpilot import coreset as CS
    from tsfpilot import detector as D
    from tsfpilot import scoring as S
    cfg, dcfg, dev = ctx["cfg"], ctx["cfg"]["detector"], ctx["device"]
    gate = access.FrameGate(ctx["root"], cfg)
    keys = [(f, s) for f in sorted(cfg["folds"]) for s in dcfg["coreset_seeds"]]
    coresets = {k: S.Coreset(CS.load(ctx["frozen"], *k)[1], dev) for k in keys}
    last = SMOKE["validation_last"] if ctx["smoke"] else gate.val_frames[-1]
    frames = list(range(gate.val_frames[0], last + 1))
    maps = {k: np.empty((len(frames), 80, 100), np.float32) for k in keys}
    frame1 = None
    bs = dcfg["batch_size"]
    for a in range(0, len(frames), bs):
        batch = gate.batch("validation", None, [(gate.val_scenario, f) for f in frames[a:a + bs]])
        feats = D.extract(net, batch.images, dcfg, dev)
        if a == 0:
            frame1 = feats[0].clone()
        for k in keys:
            maps[k][a:a + len(batch.keys)] = S.anomaly_maps(feats, batch.purpose, coresets[k])
    files = {}
    for (fold, seed), m in maps.items():
        if not np.all(np.isfinite(m)):
            raise FloatingPointError(f"non-finite validation map for {fold} seed {seed} (section 20: abort)")
        p = os.path.join(ctx["frozen"], f"validation_maps_{fold}_seed{seed}.npy")
        np.save(p, m)
        files[os.path.basename(p)] = C.file_sha256(p)
    at01 = AT.at01(trace, maps[keys[0]].shape[1:])
    at03 = {fold: AT.at03(frame1, coresets[(fold, dcfg["coreset_seeds"][0])], fold) for fold in sorted(cfg["folds"])}
    at04a, batch4 = AT.at04a(net, gate, coresets, dcfg, dev)
    n = min(8, len(frames))                                  # frames 1 to 8 share their batch composition
    at04a["main_pass_equals_rerun_frames_1_to_8"] = all(bool(np.array_equal(maps[k][:n], batch4[k][:n]))
                                                        for k in keys)
    at04b = AT.at04b(net, gate, coresets, dcfg, dev, batch4)
    del coresets
    torch.cuda.empty_cache()
    tests = [at01, at04a, at04b] + list(at03.values())
    return {"phase": "D", "validation_frames": [frames[0], frames[-1]], "validation_map_files": files,
            "AT-01": at01, "AT-03": at03, "AT-04a": at04a, "AT-04b": at04b,
            "reads": gate.read_summary(), "read_violations": gate.audit_reads(),
            "pass": all(t["pass"] for t in tests) and not gate.audit_reads()}


def phase_e(ctx):
    from tsfpilot import validation as V
    cfg = ctx["cfg"]
    gate = access.FrameGate(ctx["root"], cfg)
    a = json.load(open(os.path.join(ctx["out"], "phase_A.json")))
    constants = {"tau_r": {f: a["folds"][f]["tau_r"]["tau_r"] for f in sorted(cfg["folds"])}, "per_fold_seed": {}}
    for fold in sorted(cfg["folds"]):
        vm = dict(np.load(os.path.join(ctx["out"], "motion", f"validation_motion_{fold}.npz")))
        for seed in cfg["detector"]["coreset_seeds"]:
            maps = np.load(os.path.join(ctx["frozen"], f"validation_maps_{fold}_seed{seed}.npy"))
            n = len(maps)
            labels = gate.validation_labels()[:n]
            vmn = {k: v[:n] for k, v in vm.items()}
            c = V.map_constants(maps)
            stem = os.path.join(ctx["frozen"], f"{fold}_seed{seed}")
            np.save(stem + "_b1.npy", c["b1"])
            np.save(stem + "_b3.npy", c["b3"])
            constants["per_fold_seed"][f"{fold} seed {seed}"] = {
                "mu0": c["mu0"], "tau_cell": c["tau_cell"], "b1_column_profile": c["b1_column_profile"],
                "deployment_thresholds": V.deployment_thresholds(maps, labels, vmn, c["mu0"], cfg),
                "validation_frames": n}
    dump(os.path.join(ctx["frozen"], "stage2_constants.json"), constants)
    with open(os.path.join(ctx["frozen"], "requirements.lock"), "w") as f:
        f.write(subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True).stdout)
    frozen = {os.path.basename(p): {"bytes": os.path.getsize(p), "sha256": C.file_sha256(p)}
              for p in sorted(glob.glob(os.path.join(ctx["frozen"], "*")))}
    dump(os.path.join(ctx["out"], "frozen_manifest.json"), frozen)
    return {"phase": "E", "constants_sha256": frozen["stage2_constants.json"]["sha256"],
            "frozen_manifest_sha256": C.file_sha256(os.path.join(ctx["out"], "frozen_manifest.json")),
            "reads": gate.read_summary(), "read_violations": gate.audit_reads(),
            "pass": not gate.audit_reads()}


def gpu_environment(dev):
    import torch
    from tsfpilot import detector as D
    env = {"device": str(dev), "determinism": D.determinism_flags(), "weights": D.weights_file_sha256()}
    for mod in ("faiss", "timm", "tqdm"):
        try:
            env[mod] = __import__(mod).__version__
        except Exception:                                   # noqa: BLE001
            env[mod] = None
    try:
        env["nvidia_smi"] = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total",
                                            "--format=csv,noheader"], capture_output=True, text=True).stdout.strip()
    except FileNotFoundError:
        env["nvidia_smi"] = None
    env["torch_cuda_available"] = torch.cuda.is_available()
    return env


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset-root", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--work", default=None, help="scratch folder for the bank feature arrays (about 10 GB per fold)")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--allow-cpu", action="store_true", help="smoke runs only")
    a = ap.parse_args()
    cfg = C.load()
    root = find_root(a.dataset_root)
    if root is None:
        sys.exit("dataset not found (--dataset-root)")
    out = os.path.abspath(a.out)
    ctx = {"cfg": cfg, "root": root, "out": out, "frozen": os.path.join(out, "frozen"),
           "work": a.work or os.path.join(out, "work"), "workers": a.workers, "smoke": a.smoke}
    os.makedirs(ctx["frozen"], exist_ok=True)
    os.makedirs(ctx["work"], exist_ok=True)
    started = now()
    pre = preconditions(cfg)
    if pre["problems"] and not a.smoke:
        dump(os.path.join(out, "stage2_report.json"), {"stage": 2, "result": "FAIL", "preconditions": pre})
        sys.exit("preconditions failed: " + "; ".join(pre["problems"]))

    import torch
    from tsfpilot import detector as D
    D.set_determinism()
    dev = torch.device("cuda:0") if torch.cuda.is_available() else None
    if dev is None and not (a.smoke and a.allow_cpu):
        sys.exit("Stage 2 needs a GPU (section 24); --smoke --allow-cpu is for dry runs only")
    ctx["device"] = dev or torch.device("cpu")

    phases = {}
    net = None
    for name in ("0", "A", "B", "C", "D", "E"):
        path = os.path.join(out, f"phase_{name}.json")
        if os.path.exists(path):
            phases[name] = json.load(open(path))
        else:
            if name in ("B", "C", "D") and net is None:
                net = D.load_backbone(ctx["device"])
            t0 = time.time()
            print(f"[{now()}] phase {name} ...", flush=True)
            if name == "0":
                rec = phase_0(ctx)
            elif name == "A":
                rec = phase_a(ctx)
            elif name == "B":
                rec = phase_b(ctx, net)
            elif name == "C":
                rec = phase_c(ctx, net)
            elif name == "D":
                rec = phase_d(ctx, net, [(k, tuple(v)) for k, v in phases["B"]["trace"]])
            else:
                rec = phase_e(ctx)
            rec["seconds"] = round(time.time() - t0, 1)
            rec["finished_utc"] = now()
            dump(path, rec)
            phases[name] = rec
        print(f"[{now()}] phase {name}: {'pass' if phases[name]['pass'] else 'FAIL'}", flush=True)
        if not phases[name]["pass"] and not a.smoke:          # a smoke run continues to exercise every phase
            break

    acceptance = {}
    if "A" in phases:
        for f, r in phases["A"]["folds"].items():
            acceptance[f"AT-06b {f}"] = r["AT-06b"]["pass"]
    if "B" in phases:
        acceptance["AT-02"] = phases["B"]["AT-02"]["pass"]
    if "D" in phases:
        acceptance["AT-01"] = phases["D"]["AT-01"]["pass"]
        for f, r in phases["D"]["AT-03"].items():
            acceptance[f"AT-03 {f}"] = r["pass"]
        acceptance["AT-04a"] = phases["D"]["AT-04a"]["pass"]
        acceptance["AT-04b"] = phases["D"]["AT-04b"]["pass"]
    complete = all(n in phases for n in ("0", "A", "B", "C", "D", "E"))
    failed = any(not p["pass"] for p in phases.values())
    result = "FAIL" if failed else ("SMOKE" if a.smoke else ("PASS" if complete else "INCOMPLETE"))
    hashes, fingerprint = source_hashes()
    report = {"stage": 2, "spec": "Research Gate v1.2 + v1.2.1; clarifications DL-0013", "result": result,
              "smoke": a.smoke, "started_utc": started, "finished_utc": now(), "preconditions": pre,
              "acceptance": acceptance, "phases": {n: {k: v for k, v in p.items() if k != "reads"}
                                                   for n, p in phases.items()},
              "reads": {n: p.get("reads", []) for n, p in phases.items()},
              "environment": dict(environment(), gpu=gpu_environment(ctx["device"])),
              "coreset_seeds": cfg["detector"]["coreset_seeds"], "hashes": hashes, "files_fingerprint": fingerprint}
    rp = os.path.join(out, "stage2_report.json")
    dump(rp, report)
    print(f"Stage 2 {result}  {acceptance}\nreport {rp}  sha256 {C.file_sha256(rp)}\nfiles fingerprint {fingerprint}")
    sys.exit(0 if result in ("PASS", "SMOKE") else 1)


if __name__ == "__main__":
    main()
