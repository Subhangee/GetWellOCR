r"""Old cleanup vs new adaptive cleanup on one image, side by side.

Run:   python scripts\compare_cleanup.py data\degraded\medplan_001__noise_3.png
Output: outputs/figures/compare_<image name>.png  (raw | old | new)
        plus what OCR found in each version, printed in the terminal.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2
import numpy as np

from src import config
from src.evaluate import score_document
from src.extract import read_text
from src.parse import parse_lines
from src.preprocess import deskew, denoise, enhance_contrast, load_image, preprocess, to_gray
from src.schema import ExtractionResult


def old_cleanup(img):
    """Version 1: the same fixed steps for every image."""
    out = denoise(to_gray(img), strength=10)
    out = enhance_contrast(out)
    out, angle = deskew(out)
    return out, ["gray", "denoise (h=10, always)", "contrast (always)", f"deskew ({angle:+.2f} deg)"]


def label(img, text):
    """Resize to a common height and write a title bar on top."""
    h = 1100
    small = cv2.resize(img, (int(img.shape[1] * h / img.shape[0]), h), interpolation=cv2.INTER_AREA)
    bar = np.full((70, small.shape[1]), 255, np.uint8)
    cv2.putText(bar, text, (20, 48), cv2.FONT_HERSHEY_SIMPLEX, 1.4, 0, 3)
    return np.vstack([bar, small])


def main():
    if len(sys.argv) < 2:
        print(r"Usage: python scripts\compare_cleanup.py data\degraded\medplan_001__noise_3.png")
        return
    path = Path(sys.argv[1])
    img = load_image(path)
    raw = to_gray(img)
    old, old_log = old_cleanup(img)
    new, new_log = preprocess(img)

    doc_id = path.stem.split("__")[0]
    truth_file = config.GROUND_TRUTH_DIR / f"{doc_id}.json"
    truth = (ExtractionResult.model_validate_json(truth_file.read_text(encoding="utf-8"))
             if truth_file.exists() else None)

    for name, image, log in (("RAW", raw, ["no cleanup"]), ("OLD", old, old_log), ("NEW", new, new_log)):
        result = parse_lines(read_text(image, "tesseract"), doc_id, "tesseract")
        print(f"\n=== {name} ===")
        print("steps: " + " -> ".join(log))
        for m in result.medications:
            print(f"  {m.name:<22} {m.strength or '-':<10} {m.dosing or '-'}")
        if not result.medications:
            print("  (no medications found)")
        if truth:
            s = score_document(result, truth)
            print(f"  medication F1 {s['med_f1']:.2f} | dosing accuracy {s['dosing_accuracy']:.2f}")

    panels = [label(raw, "RAW"), label(old, "OLD cleanup"), label(new, "NEW adaptive cleanup")]
    sheet = np.hstack([np.pad(p, ((0, 0), (0, 30)), constant_values=255) for p in panels])
    out = config.FIGURE_DIR / f"compare_{path.stem}.png"
    cv2.imwrite(str(out), sheet)
    print(f"\nSaved {out}")


if __name__ == "__main__":
    main()
