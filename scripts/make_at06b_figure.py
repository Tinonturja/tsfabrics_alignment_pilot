"""Draw the AT-06b figure (why the Stage 2 rerun stopped) from the committed Stage 2 record.

Reads only audit/stage2_kaggle_v1_2_2_FAIL/stage2_record.zip (validation-side numbers; no image, no test scenario)
after checking its SHA-256 against the value recorded in DL-0024. Writes figures/at06b_direction_check.svg and .png.

Usage: python scripts/make_at06b_figure.py
"""
import hashlib
import io
import json
import os
import zipfile

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RECORD = os.path.join(REPO, "audit", "stage2_kaggle_v1_2_2_FAIL", "stage2_record.zip")
RECORD_SHA256 = "4bea162bc39e7c515c8655305f90921ec54434bcd8495c81c1d733c7c6ca9d09"   # DL-0024
OUT = os.path.join(REPO, "figures", "at06b_direction_check")

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#d9d8d4"
HOLDS, FAILS = "#2a78d6", "#eb6834"          # categorical slots 1 and 2 of the reference palette


def load_pairs():
    data = open(RECORD, "rb").read()
    got = hashlib.sha256(data).hexdigest()
    if got != RECORD_SHA256:
        raise SystemExit(f"record hash {got} differs from DL-0024")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        at = json.load(z.open("phase_A.json"))["folds"]["A-G1"]["AT-06b"]
    cols = at["columns"]
    rows = [dict(zip(cols, r)) for r in at["pairs"]]
    return at, rows


def main():
    at, rows = load_pairs()
    held = [r for r in rows if r["holds"]]
    failed = [r for r in rows if not r["holds"]]
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID,
                         "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                         "svg.fonttype": "none"})
    fig = plt.figure(figsize=(8.6, 7.0), facecolor=SURFACE)
    gs = fig.add_gridspec(2, 1, height_ratios=[1, 5.2], hspace=0.55, left=0.1, right=0.97, top=0.83, bottom=0.14)

    fig.text(0.1, 0.955, "The direction check could not tell the measured shift from its reverse",
             fontsize=13, fontweight="bold", color=INK)
    fig.text(0.1, 0.915, f"AT-06b, fold A-G1: {at['holding']} of {len(rows)} frame pairs held; "
             f"{at['required']} were needed. Validation-side scenario T1_S164_I192_1.",
             fontsize=9.5, color=INK2)
    fig.text(0.1, 0.885, "A pair holds when warping by the measured shift U fits better than warping by -U.",
             fontsize=9.5, color=INK2)

    # (a) outcome of each pair in frame order
    ax = fig.add_subplot(gs[0], facecolor=SURFACE)
    for i, r in enumerate(rows):
        ax.add_patch(Rectangle((i + 0.1, 0), 0.8, 1, color=HOLDS if r["holds"] else FAILS, lw=0))
    ax.set_xlim(0, len(rows))
    ax.set_ylim(0, 1)
    ax.set_yticks([])
    ax.set_xticks([0, 50, 100, 150, 200])
    ax.set_xlabel("pair index in frame order (t = 2 to 201)", fontsize=9)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("(a) Long runs of both outcomes, not a scatter of errors", loc="left", fontsize=10, color=INK)

    # (b) fit of +U and -U relative to no warp
    bx = fig.add_subplot(gs[1], facecolor=SURFACE)
    lo, hi = 0.3, 3.6
    bx.set_xscale("log")
    bx.set_yscale("log")
    bx.set_xlim(lo, hi)
    bx.set_ylim(lo, hi)
    bx.fill_between([1, hi], 1, hi, color=GRID, alpha=0.35, lw=0, zorder=0)
    bx.plot([lo, hi], [lo, hi], color=INK2, lw=1, ls="--", zorder=1)
    bx.axvline(1, color=GRID, lw=1, zorder=1)
    bx.axhline(1, color=GRID, lw=1, zorder=1)
    kw = dict(s=26, edgecolors=SURFACE, linewidths=0.8, zorder=3)
    bx.scatter([r["mse_U"] / r["mse_zero_shift"] for r in held], [r["mse_minus_U"] / r["mse_zero_shift"] for r in held],
               color=HOLDS, marker="o", label=f"holds: +U fits better ({len(held)})", **kw)
    bx.scatter([r["mse_U"] / r["mse_zero_shift"] for r in failed],
               [r["mse_minus_U"] / r["mse_zero_shift"] for r in failed],
               color=FAILS, marker="^", label=f"fails: -U fits better ({len(failed)})", **kw)
    zero_best = sum(r["mse_U"] > r["mse_zero_shift"] and r["mse_minus_U"] > r["mse_zero_shift"] for r in rows)
    bx.text(3.35, 3.0, "equal fit", color=INK2, fontsize=9, ha="right", rotation=45, rotation_mode="anchor")
    bx.text(3.4, 1.06, f"no warp beats both: {zero_best} of {len(rows)} pairs", color=INK2, fontsize=9, ha="right")
    ticks = [0.5, 1, 2, 3]
    bx.set_xticks(ticks, [str(t) for t in ticks])
    bx.set_yticks(ticks, [str(t) for t in ticks])
    bx.minorticks_off()
    bx.set_xlabel("error after warping by measured shift +U  (relative to no warp)")
    bx.set_ylabel("error after warping by -U  (relative to no warp)")
    bx.set_title("(b) Both warps fit worse than no warp, and about equally badly", loc="left", fontsize=10, color=INK)
    leg = bx.legend(loc="upper left", frameon=False, fontsize=9)
    for t in leg.get_texts():
        t.set_color(INK)
    for s in ("top", "right"):
        bx.spines[s].set_visible(False)

    fig.text(0.1, 0.035, "Errors are mean squared differences of 8 x 8 block-mean images, over columns valid for both warps.",
             fontsize=8, color=INK2)
    fig.text(0.1, 0.012, "The fabric pattern repeats about every 85 px and the fabric moves about 86 px per frame, so a shift "
             "and its reverse look alike.", fontsize=8, color=INK2)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT + ".svg", facecolor=SURFACE, metadata={"Date": None})
    fig.savefig(OUT + ".png", dpi=200, facecolor=SURFACE)
    print("wrote", OUT + ".svg", OUT + ".png")


if __name__ == "__main__":
    main()
