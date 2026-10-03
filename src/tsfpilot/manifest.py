"""Hashing and run records (section 25)."""
import hashlib
import json
import os
import platform
import subprocess
import sys

from .config import REPO, file_sha256


def git_state(repo=REPO):
    def run(*a):
        try:
            return subprocess.run(["git", *a], cwd=repo, capture_output=True, text=True, timeout=20).stdout.strip()
        except Exception:
            return ""
    commit = run("rev-parse", "HEAD")
    dirty = run("status", "--porcelain")
    return {"commit": commit or None, "clean": commit != "" and dirty == ""}


def environment():
    env = {"python": sys.version, "platform": platform.platform()}
    for mod in ("numpy", "scipy", "pandas", "numba", "yaml", "cv2", "torch", "torchvision"):
        try:
            env[mod] = __import__(mod).__version__
        except Exception:
            env[mod] = None
    try:
        import torch
        env["cuda"] = torch.version.cuda
        env["cudnn"] = torch.backends.cudnn.version()
        env["gpu"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    except Exception:
        pass
    return env


def manifest(paths, extra=None):
    files = []
    for p in sorted(paths):
        files.append({"path": os.path.relpath(p, REPO), "bytes": os.path.getsize(p), "sha256": file_sha256(p)})
    m = {"files": files, "git": git_state(), "environment": environment()}
    if extra:
        m.update(extra)
    blob = json.dumps(m, sort_keys=True, indent=1).encode()
    return m, hashlib.sha256(blob).hexdigest(), blob


def frame_list_sha256(paths):
    """SHA-256 of the sorted list of (image path, byte size) for every frame used (section 25)."""
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(f"{p}\t{os.path.getsize(p)}\n".encode())
    return h.hexdigest()
