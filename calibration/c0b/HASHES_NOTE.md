# Note on HASHES.txt

`HASHES.txt` records the calibration files as they were when the calibration ran (2026-09-30).
Every entry verifies with `sha256sum -c HASHES.txt` except one, by design:

| File | Hash in HASHES.txt (as run) | Hash in this repository | Difference |
|---|---|---|---|
| `layout.py` | `dc48ed89bac61636d53c002a1cb14d831f8e9be391c3fb407618b6b4fa0eb743` | `3f44ca357370176f2a7fcfceb775b7f28eeda8f3290d482f27d380864fea85a2` | Only the line that locates `tsfabrics_pilot_passes_and_candidate_tracks.csv`: an absolute path from the original run environment was replaced by a path relative to the repository (decision log DL-0009, I-9). The layout logic is unchanged |

The original line was:

```python
P=pd.read_csv('<original run directory>/tsfabrics_pilot_passes_and_candidate_tracks.csv')
```

Evidence that nothing else changed: `tests/test_at15_chance.py` reproduces the calibration kernel's result exactly on all
200 traces of the amendment's regression cell using this `layout.py`, and the frozen CSV it reads is hashed in
`audit/stage1_report*.json`.
