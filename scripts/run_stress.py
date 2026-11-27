r"""Run the whole-case pipeline on every damage type and level, and score each run.

Needs:  python scripts\make_stress_set.py   (creates data/cases/<case>/stress/)

Run:    python scripts\run_stress.py                    all 6 types x 4 levels (~20 min with Tesseract)
        python scripts\run_stress.py --quick            levels 2 and 4 only (~10 min)
        python scripts\run_stress.py --types blur fax   only some types
        python scripts\run_stress.py --case case01_hard

Writes: outputs/stress/<case>/results.csv          one row per type and level
        outputs/stress/<case>/<type>/L<n>/case_result.json
        outputs/figures/stress_<case>.png           the robustness chart for the pitch
OCR results are cached, so a second run (e.g. after changing the rules) takes seconds.
"""
import argparse
import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config
from src.case import process_case
from src.evaluate import score_case


def run(folder: Path, out_dir: Path, engine: str, answers: dict) -> dict:
    t0 = time.time()
    result = process_case(folder, out_dir, engine, progress=lambda *_: None)
    sc = score_case(result, answers)
    sc["seconds"] = round(time.time() - t0, 1)
    return sc


def plot(rows: list[dict], case: str, total: int):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    baseline = next(r for r in rows if r["type"] == "clean")
    types = [t for t in dict.fromkeys(r["type"] for r in rows) if t != "clean"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.6))
    for t in types:
        pts = [(0, baseline["needles_found"])] + [(r["level"], r["needles_found"]) for r in rows if r["type"] == t]
        a1.plot(*zip(*pts), marker="o", label=t)
        pts = [(0, len(baseline["retake"]))] + [(r["level"], len(r["retake"])) for r in rows if r["type"] == t]
        a2.plot(*zip(*pts), marker="o", label=t)
    a1.set(title=f"Critical facts found ({case}, of {total})", xlabel="damage level (0 = clean, 4 = almost unreadable)",
           ylabel="facts found", ylim=(0, total + 0.5), xticks=range(5))
    a2.set(title="Pages sent back: 'please retake'", xlabel="damage level", ylabel="pages (of 20)",
           ylim=(0, 20.5), xticks=range(5))
    a1.grid(alpha=0.3)
    a2.grid(alpha=0.3)
    a1.legend(loc="lower left", fontsize=8)
    fig.tight_layout()
    out = config.FIGURE_DIR / f"stress_{case}.png"
    fig.savefig(out, dpi=160)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default="case01")
    ap.add_argument("--engine", default=config.OCR_ENGINE)
    ap.add_argument("--types", nargs="*")
    ap.add_argument("--quick", action="store_true", help="levels 2 and 4 only")
    ap.add_argument("--best-of", action=argparse.BooleanOptionalAction, default=None,
                    help="default: OCR_BEST_OF in .env (on). --no-best-of is about 4x faster")
    args = ap.parse_args()
    if args.best_of is not None:
        config.OCR_BEST_OF = args.best_of

    case_dir = config.DATA_DIR / "cases" / args.case
    stress = case_dir / "stress"
    if not (stress / "manifest.json").exists():
        print(f"No stress set for {args.case}. Run: python scripts\\make_stress_set.py --case {args.case}")
        return
    manifest = json.loads((stress / "manifest.json").read_text(encoding="utf-8"))
    answers = json.loads((case_dir / f"{args.case}_answers.json").read_text(encoding="utf-8"))
    types = args.types or list(manifest["types"])
    levels = [2, 4] if args.quick else manifest["levels"]
    out_root = config.OUTPUT_DIR / "stress" / args.case

    jobs = [("clean", 0, case_dir / "pages_clean")] + \
           [(t, lv, stress / t / f"L{lv}") for t in types for lv in levels]
    rows = []
    for i, (kind, level, folder) in enumerate(jobs, 1):
        sc = run(folder, out_root / kind / f"L{level}", args.engine, answers)
        setting = manifest["types"].get(kind, {}).get("settings", [None] * 4)[level - 1] if level else None
        rows.append({"type": kind, "level": level, "setting": setting, **sc})
        print(f"[{i:2d}/{len(jobs)}] {kind:<7} L{level}  facts {sc['needles_found']:2d}/{sc['needles_total']}  "
              f"pages correct {sc['pages_correct']:2d}/{sc['pages_classified']:<2d}  retake {len(sc['retake']):2d}  "
              f"({sc['seconds']} s)")

    out_root.mkdir(parents=True, exist_ok=True)
    cols = ["type", "level", "setting", "needles_found", "needles_total", "pages_correct", "pages_classified",
            "retake", "conflicts_flagged", "conflicts_truth", "seconds", "missed"]
    with open(out_root / "results.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter=";", extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({**r, "retake": len(r["retake"]),
                        "missed": " ".join(n["id"] for n in r["needles"] if not n["found"])})
    fig = plot(rows, args.case, answers and len(answers["needles"]))
    print(f"\nSaved {out_root / 'results.csv'}\nSaved {fig}")


if __name__ == "__main__":
    main()
