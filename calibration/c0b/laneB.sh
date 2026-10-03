set -x
python3 amend.py A1_uniform uniform zero 2000 A-G1,A-G4 N1_iid N2_ar0.9 N3_ar0.99 N4_drift N5_offsets N6_periodic N7_trend N8_composite N9_ties
python3 amend.py D2_nophase nophase zero 1000 A-G1 N3_ar0.99 N4_drift N6_periodic N7_trend N8_composite
python3 amend.py D1_seam v12 seam 1000 A-G1 N3_ar0.99 N4_drift N6_periodic N7_trend N8_composite
python3 amend.py power_v12 v12 zero 500 A-G1,A-G4 S_0.25 S_0.5
python3 amend.py power_A1 uniform zero 500 A-G1,A-G4 S_0.25 S_0.5
echo LANE_B_DONE
