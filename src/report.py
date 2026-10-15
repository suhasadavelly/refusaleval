"""Chart and summarize the newest labeled results file.

Usage:  python src/report.py                               (newest *.labeled.jsonl)
        python src/report.py results/<file>.labeled.jsonl  (a specific file)

Reads the file judge.py wrote, prints the key numbers, and saves four PNGs
under reports/<run>/. Never overwrites existing files. The label field name is
detected from the data, not assumed.
"""
import collections
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # no display needed; we only save PNGs
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent

# The four labels judge.py can assign (see NOTES.md).
LABELS = ["refused", "partial", "complied", "incoherent"]
LABEL_SET = set(LABELS)

# Palette (from the dataviz reference palette, light surface). Color follows the
# entity: harmful = blue, benign = orange, used consistently across charts.
BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#d9d8d4"


def newest_labeled():
    files = list((ROOT / "results").glob("*.labeled.jsonl"))
    if not files:
        sys.exit("No results/*.labeled.jsonl files. Run src/judge.py first.")
    return max(files, key=lambda p: p.name)  # timestamped names sort chronologically


def detect_label_field(rows):
    """Find the field that holds the label, rather than assuming it is called 'label'."""
    keys = list(rows[0].keys())
    if "label" in keys and all(r.get("label") in LABEL_SET for r in rows):
        return "label"
    for k in keys:  # fall back: any field whose values are all valid labels
        if all(r.get(k) in LABEL_SET for r in rows):
            return k
    sys.exit("Could not find a label field (values in {refused,partial,complied,incoherent}).")


def style(ax):
    """Recessive axes: drop the box, keep a faint value-axis grid."""
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=MUTED, length=0)
    ax.title.set_color(INK)


def save(fig, path):
    if path.exists():  # never overwrite
        sys.exit(f"{path} already exists; not overwriting. Remove reports/{path.parent.name}/ to rebuild.")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  wrote {path.relative_to(ROOT)}")


def rate(rows, label="refused"):
    """Fraction of rows with the given label (0..1); 0 for an empty group."""
    return sum(1 for r in rows if r["_label"] == label) / len(rows) if rows else 0.0


def chart_label_breakdown(rows, out):
    counts = collections.Counter(r["_label"] for r in rows)
    values = [counts.get(l, 0) for l in LABELS]
    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(LABELS, values, color=BLUE, width=0.6)
    ax.bar_label(bars, padding=3, color=INK, fontsize=10)
    ax.set_ylim(0, max(values) * 1.15 or 1)
    ax.set_ylabel("replies", color=MUTED)
    ax.set_title("Overall label breakdown", fontsize=13, loc="left")
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    style(ax)
    save(fig, out / "1_label_breakdown.png")


def chart_refusal_by_category(rows, out):
    cats = collections.defaultdict(list)
    for r in rows:
        cats[r["category"]].append(r)
    # sorted by refusal rate (magnitude), highest at top of a horizontal chart
    items = sorted(cats.items(), key=lambda kv: rate(kv[1]))
    names = [c for c, _ in items]
    rates = [rate(rs) * 100 for _, rs in items]
    # color by whether the category is harmful (expected refuse) or benign
    colors = [BLUE if items[i][1][0]["expected"] == "refuse" else ORANGE for i in range(len(items))]
    fig, ax = plt.subplots(figsize=(7, 6))
    bars = ax.barh(names, rates, color=colors, height=0.7)
    ax.bar_label(bars, fmt="%.0f%%", padding=3, color=INK, fontsize=9)
    ax.set_xlim(0, 108)
    ax.set_xlabel("refusal rate (%)", color=MUTED)
    ax.set_title("Refusal rate by category", fontsize=13, loc="left")
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    style(ax)
    handles = [plt.Rectangle((0, 0), 1, 1, color=BLUE), plt.Rectangle((0, 0), 1, 1, color=ORANGE)]
    ax.legend(handles, ["harmful (want refuse)", "benign (want comply)"], frameon=False,
              fontsize=9, loc="lower right", labelcolor=MUTED)
    save(fig, out / "2_refusal_by_category.png")


def chart_harmful_vs_benign(rows, out):
    harmful = [r for r in rows if r["expected"] == "refuse"]
    benign = [r for r in rows if r["expected"] == "comply"]
    groups = ["harmful\n(want refuse)", "benign\n(want comply)"]
    rates = [rate(harmful) * 100, rate(benign) * 100]
    fig, ax = plt.subplots(figsize=(5, 4))
    bars = ax.bar(groups, rates, color=[BLUE, ORANGE], width=0.55)
    ax.bar_label(bars, fmt="%.0f%%", padding=3, color=INK, fontsize=11)
    ax.set_ylim(0, 108)
    ax.set_ylabel("refusal rate (%)", color=MUTED)
    ax.set_title("Refusal rate: harmful vs benign", fontsize=13, loc="left")
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    style(ax)
    save(fig, out / "3_harmful_vs_benign.png")


def chart_jailbreak_vs_plain(rows, out):
    jailbreak = [r for r in rows if r["category"] == "jailbreak"]
    plain = [r for r in rows if r["expected"] == "refuse" and r["category"] != "jailbreak"]
    groups = [f"jailbreak\n(n={len(jailbreak)})", f"plain-harmful\n(n={len(plain)})"]
    rates = [rate(jailbreak) * 100, rate(plain) * 100]
    fig, ax = plt.subplots(figsize=(5, 4))
    bars = ax.bar(groups, rates, color=BLUE, width=0.55)
    ax.bar_label(bars, fmt="%.0f%%", padding=3, color=INK, fontsize=11)
    ax.set_ylim(0, 108)
    ax.set_ylabel("refusal rate (%)", color=MUTED)
    ax.set_title("Refusal rate: jailbreak vs plain-harmful", fontsize=13, loc="left")
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    style(ax)
    save(fig, out / "4_jailbreak_vs_plain.png")


def print_summary(rows):
    counts = collections.Counter(r["_label"] for r in rows)
    harmful = [r for r in rows if r["expected"] == "refuse"]
    benign = [r for r in rows if r["expected"] == "comply"]
    jailbreak = [r for r in rows if r["category"] == "jailbreak"]
    plain = [r for r in rows if r["expected"] == "refuse" and r["category"] != "jailbreak"]

    print(f"\n{len(rows)} replies. Labels: " + ", ".join(f"{l}={counts.get(l, 0)}" for l in LABELS))
    print("(refusal rate counts only 'refused'; 'partial' is shown separately in the breakdown.)\n")
    print(f"Harmful prompts (expected refuse):  n={len(harmful)}")
    print(f"  refusal rate (good):     {rate(harmful) * 100:5.1f}%")
    print(f"  compliance rate (bad):   {rate(harmful, 'complied') * 100:5.1f}%")
    print(f"Benign prompts (expected comply):   n={len(benign)}")
    print(f"  over-refusal rate (bad): {rate(benign) * 100:5.1f}%")
    print(f"  compliance rate (good):  {rate(benign, 'complied') * 100:5.1f}%")
    print(f"Jailbreak refusal rate:    {rate(jailbreak) * 100:5.1f}%  (n={len(jailbreak)})")
    print(f"Plain-harmful refusal rate:{rate(plain) * 100:5.1f}%  (n={len(plain)})")


def main():
    in_path = Path(sys.argv[1]) if len(sys.argv) > 1 else newest_labeled()
    if not in_path.is_absolute():
        in_path = ROOT / in_path

    rows = [json.loads(line) for line in open(in_path, encoding="utf-8")]
    if not rows:
        sys.exit(f"{in_path.name} is empty.")
    field = detect_label_field(rows)
    for r in rows:  # normalize onto a known key so the rest of the code is simple
        r["_label"] = r[field]

    out = ROOT / "reports" / in_path.name.replace(".labeled.jsonl", "")
    if out.exists():
        sys.exit(f"{out} already exists; not overwriting. Remove it to rebuild.")
    out.mkdir(parents=True)

    print(f"Reading {in_path.name} (label field: '{field}')")
    print(f"Charts -> {out.relative_to(ROOT)}/")
    chart_label_breakdown(rows, out)
    chart_refusal_by_category(rows, out)
    chart_harmful_vs_benign(rows, out)
    chart_jailbreak_vs_plain(rows, out)
    print_summary(rows)


if __name__ == "__main__":
    main()
