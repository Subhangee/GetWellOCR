r"""Run the test cases with each OCR engine and print the scorecards side by side.

Run:   python scripts\compare_engines.py
       python scripts\compare_engines.py --engines tesseract paddle --no-best-of
       add --fresh to ignore cached OCR

Output: outputs/engines/engine_comparison.csv
        (each run's case_result.json is in outputs/engines/<case>/<engine>/)
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engines", nargs="+", default=["tesseract", "paddle"])
    ap.add_argument("--cases", nargs="+", default=["case01", "case01_hard"])
    ap.add_argument("--best-of", action=argparse.BooleanOptionalAction, default=None,
                    help="default: OCR_BEST_OF in .env (on)")
    ap.add_argument("--classifier", choices=["rules", "model", "hybrid"], help="default: CLASSIFIER in .env / config")
    ap.add_argument("--fresh", action="store_true")
    args = ap.parse_args()
    if args.best_of is not None:
        config.OCR_BEST_OF = args.best_of
    if args.classifier:
        config.CLASSIFIER = args.classifier

    out_root = config.OUTPUT_DIR / "engines"
    rows = []
    for case in args.cases:
        case_dir = config.DATA_DIR / "cases" / case
        answers = json.loads((case_dir / f"{case}_answers.json").read_text(encoding="utf-8"))
        for engine in args.engines:
            print(f"{case} · {engine} ...", flush=True)
            start = time.time()
            try:
                result = process_case(case_dir / "pages_photo", out_root / case / engine, engine,
                                      args.fresh, progress=lambda *_: None)
            except Exception as e:          # engine not installed, models missing, no Azure key ...
                print(f"   failed: {e}")
                continue
            sc = score_case(result, answers)
            rows.append({
                "case": case, "engine": engine, "best_of": config.OCR_BEST_OF,
                "facts": f"{sc['needles_found']}/{sc['needles_total']}",
                "pages_correct": f"{sc['pages_correct']}/{sc['pages_classified']}",
                "retake": len(sc["retake"]),
                "conflicts": f"{sc['conflicts_flagged']} (truth {sc['conflicts_truth']})",
                "missed": " ".join(n["id"] for n in sc["needles"] if not n["found"]) or "-",
                "seconds": round(time.time() - start),
            })

    if not rows:
        print("No engine ran successfully.")
        return
    cols = list(rows[0])
    widths = {c: max(len(c), *(len(str(r[c])) for r in rows)) for c in cols}
    print()
    print("  ".join(c.ljust(widths[c]) for c in cols))
    for r in rows:
        print("  ".join(str(r[c]).ljust(widths[c]) for c in cols))
    print("\n(seconds are near 0 when cached OCR was reused; add --fresh to time a real run)")

    out_root.mkdir(parents=True, exist_ok=True)
    with open(out_root / "engine_comparison.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f"Saved {out_root / 'engine_comparison.csv'}")


if __name__ == "__main__":
    main()
