"""AT-17: C6 classes on the section 16 synthetic cases (within +/- 10 percentage points of the tabulated shares).
A failure means C6 is not reported; it never blocks Stage 3."""
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))

# section 16 table: (case, speed) -> (class family, tabulated count, events)
TABLE = {
    ("transient (1 frame)", "A-G1 speed"): ("transient", 40, 40),
    ("transient (1 frame)", "A-G4 speed"): ("transient", 42, 42),
    ("persistent fabric-fixed", "A-G1 speed"): ("persistent-local", 48, 49),
    ("persistent fabric-fixed", "A-G4 speed"): ("persistent-local", 41, 41),
    ("camera-fixed", "A-G1 speed"): ("camera-fixed", 52, 53),
    ("camera-fixed", "A-G4 speed"): ("camera-fixed", 44, 44),
    ("global elevation (+1.25 SD)", "A-G1 speed"): ("global-driven", 7, 7),
    ("global elevation (+1.25 SD)", "A-G4 speed"): ("global-driven", 10, 12),
    ("vertical line, fabric-fixed", "A-G1 speed"): ("diffuse", 39, 39),
    ("vertical line, fabric-fixed", "A-G4 speed"): ("diffuse", 44, 44),
    ("persistent, exit-edge start", "A-G1 speed"): ("ambiguous", 46, 47),
}


@pytest.fixture(scope="module")
def counts():
    r = subprocess.run([sys.executable, os.path.join(HERE, "fixtures", "c6_replay.py")], capture_output=True,
                       text=True, check=True)
    return json.loads(r.stdout)


def test_at17_c6_classes(counts):
    for (case, speed), (cls, k, n) in TABLE.items():
        got = counts[f"{speed}|{case}"]
        total = sum(got.values())
        hit = sum(v for c, v in got.items() if (c.startswith("ambiguous") if cls == "ambiguous" else c == cls))
        assert total > 0
        assert abs(hit / total - k / n) <= 0.10, (case, speed, got)


def test_c6_replay_reproduces_audit_exactly(counts):
    # reference/audit_b7_c6.py output for the same draws (class names mapped to the v1.2 names)
    assert counts["A-G1 speed|camera-fixed"] == {"camera-fixed": 52, "ambiguous-geometry": 1}
    assert counts["A-G4 speed|global elevation (+1.25 SD)"] == {"global-driven": 10, "transient": 1,
                                                                 "ambiguous-geometry": 1}
    assert counts["A-G1 speed|persistent, exit-edge start"] == {"ambiguous-geometry": 46, "transient": 1}
    assert counts["slow fabric|camera-fixed"] == {"camera-fixed": 56}
