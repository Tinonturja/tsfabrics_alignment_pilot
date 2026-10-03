set -x
python3 amend.py verify_repro v12 zero 2000 A-G1 N1_iid
python3 amend.py primary_AG4_N1to4 v12 zero 2000 A-G4 N1_iid N2_ar0.9 N3_ar0.99 N4_drift
python3 amend.py primary_AG4_doubled v12 zero 4000 A-G4 N6_periodic N7_trend N8_composite
python3 amend.py D3_circ_v12 v12 zero 2000 A-G1,A-G4 C3_circ0.99 C4_circ0.999
python3 amend.py D4_circ_uniform uniform zero 2000 A-G1,A-G4 C3_circ0.99 C4_circ0.999
echo LANE_A_DONE
