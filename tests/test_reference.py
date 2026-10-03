"""The frozen reference scripts still pass their own hand-computed tests (section 15 reference tests)."""
import os
import subprocess
import sys

from conftest import REF


def test_reference_metric_tests_pass():
    r = subprocess.run([sys.executable, "test_ref_metrics.py"], cwd=REF, capture_output=True, text=True)
    assert "ALL REFERENCE METRIC TESTS PASS" in r.stdout, r.stdout + r.stderr


def test_reference_bank_quotas():
    r = subprocess.run([sys.executable, "ref_bank_quota.py"], cwd=REF, capture_output=True, text=True)
    assert r.stdout.count("reproduced: True") == 2
    assert "{'T1_S164_I192_1': 50, 'T1_S164_I193_1': 50}" in r.stdout


def test_src_never_imports_reference():
    src = os.path.join(os.path.dirname(REF), "src", "tsfpilot")
    banned = ("reference", "ref_", "calibration", "c0b_kernel", "nulls", "layout")
    for f in os.listdir(src):
        if f.endswith(".py"):
            for line in open(os.path.join(src, f)):
                if line.lstrip().startswith(("import ", "from ")):
                    assert not any(b in line for b in banned), (f, line)
