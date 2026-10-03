Research Gate v1.2: reference and audit scripts (NOT experiment code; no TSFabrics images or scores).
ref_*.py        frozen reference definitions (metrics with exact rationals, decision machine, chance baseline, bank quotas)
test_ref_metrics.py   hand-computed deterministic tests (python3 test_ref_metrics.py)
audit_*.py      evidence for sections 12, 16, 18, 19, 22 of the specification
layout.py       builds each pilot fold's timeline from tsfabrics_pilot_passes_and_candidate_tracks.csv (path inside the file)
c6_synth.py     synthetic 80x100 map generator used by audit_b7_c6.py
