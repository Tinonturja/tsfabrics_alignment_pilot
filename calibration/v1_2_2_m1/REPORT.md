# M1 synthetic calibration (amendment v1.2.2, section 4): FAIL

Run 2026-10-07 in the sandbox (CPU, Python 3.11.15, numpy 2.4.4, the Kaggle numpy version), code committed
before the run (`d1c31f4`). Protocol SHA-256 `276fe983...a704` checked by the script. Output `result.json`, SHA-256
`7a82d0691f12c8c52db1673c78d8f8ba2170855a7d37554d8aa5001a6081e6ff`. Synthetic data only; no real data read.

## Result

Pooled over 200 replicates per family. "Clean" excludes warm-up, event frames and the frame after each event.

| Family | Frozen: clean consistent / reliable | M1: clean consistent / reliable | Frozen: events caught (item 3 / 4) | M1: events caught (item 3 / 4) |
|---|---|---|---|---|
| F1 steady | 100.00% / 100.00% | 100.00% / 100.00% | | |
| F2 alternating | 97.02% / 96.27% | 100.00% / 100.00% | | |
| F3 alternating + drops (not gated) | 97.02% / 96.40% | 100.00% / 100.00% | 100.00% / 100.00% | 99.57% / 99.57% |
| F4 steady + failures | 100.00% / 99.50% | 99.71% / 96.49% | 96.99% / 96.93% | 96.26% / 96.06% |
| F5 alternating + failures | 95.73% / 95.87% | 99.73% / 96.52% | 96.83% / 96.86% | 96.02% / 95.71% |
| F6 slow + drops | 99.99% / 99.99% | 99.15% / 98.25% | 100.00% / 100.00% | 100.00% / 99.45% |

Failed criteria (18 checked, 16 pass):

- Criterion 1, F6, item 4: 98.25% of clean frames reliable, limit 99%.
- Criterion 3, F4, item 4: M1's clean-frame reliability is 3.01 percentage points below the frozen rule's, limit 1.

**Verdict: M1 is not adopted.** Under section 3 C1 and section 5 the frozen motion rule stays, A-G4 stays
motion-invalid, and no second candidate is tried.

## Why it failed (explanation after the fact, not a basis for any change)

The item 4 deficit comes almost entirely from whole replicates in which M1 never becomes reliable. The first five
reliable two-frame sums enter the reliable history without a consistency check (the frozen 5-entry rule). One
estimation failure contaminates two consecutive sums, so two early failures can fill most of that seed history with
bad values. The median then sits at a wrong value and correct sums never pass again. This happened in 7 of 200 F4
replicates under M1 against 1 under the frozen rule, and in 2 of 200 F6 replicates under M1 against none. Outside
those replicates M1's per-replicate median reliability is 100% in F4 and 99.25% in F6. The frozen rule has the same
seeding weakness at a lower rate.

This explanation was obtained by inspecting the synthetic replicates after the verdict. It does not change the
verdict, and section 5 forbids further amendments of section 7.
