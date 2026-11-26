r"""Stress set A: the same 20 pages, damaged on purpose, in graded levels.

Like an SNR sweep in MRI: one kind of damage at a time, getting worse step by step,
so we can say exactly where the pipeline breaks.

  type     what it simulates                        L1 (mild) ............ L4 (almost unreadable)
  blur     out-of-focus or shaky phone photo        sigma 1.0   2.0   3.0   4.5
  noise    dark room, cheap camera, sensor noise    sigma 10    20    32    48
  skew     page photographed crooked                1.5°   4°   8°   15°
  shadow   hand/phone shadow, lamp from one side    25 %   45 %  65 %  80 % darker
  jpeg     sent through WhatsApp / e-mail           q 40   20    10    5
  fax      fax machine: low resolution, only b/w    60 %   45 %  35 %  28 % resolution

Writes (default case01):
  data/cases/case01/stress/<type>/L<level>/case01_pXX.jpg
  data/cases/case01/stress/manifest.json   one entry per image: type, level, setting, source page

Run:   python scripts\make_stress_set.py
       python scripts\make_stress_set.py --case case01_hard
The ground truth does not change: it is still <case>_answers.json.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2
import numpy as np

from src import config

LEVELS = [1, 2, 3, 4]
SETTINGS = {
    "blur":   [1.0, 2.0, 3.0, 4.5],
    "noise":  [10, 20, 32, 48],
    "skew":   [1.5, 4.0, 8.0, 15.0],
    "shadow": [0.25, 0.45, 0.65, 0.80],
    "jpeg":   [40, 20, 10, 5],
    "fax":    [0.60, 0.45, 0.35, 0.28],
}
DESCRIPTION = {
    "blur": "Gaussian blur, sigma in pixels (200 dpi page)",
    "noise": "Gaussian sensor noise, sigma in grey levels",
    "skew": "rotation in degrees",
    "shadow": "darkest corner, fraction of brightness removed (smooth gradient + soft hand shadow)",
    "jpeg": "JPEG quality (lower = more compression)",
    "fax": "fraction of the original resolution, then black/white only",
}


def blur(g, s, r):
    return cv2.GaussianBlur(g, (0, 0), s)


def noise(g, s, r):
    return np.clip(g.astype(np.float32) + r.normal(0, s, g.shape), 0, 255).astype(np.uint8)


def skew(g, angle, r):
    h, w = g.shape
    angle *= r.choice([-1, 1])
    # grow the canvas so no text is cut off at the corners
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    cos, sin = abs(m[0, 0]), abs(m[0, 1])
    nw, nh = int(h * sin + w * cos), int(h * cos + w * sin)
    m[0, 2] += nw / 2 - w / 2
    m[1, 2] += nh / 2 - h / 2
    return cv2.warpAffine(g, m, (nw, nh), borderValue=210)


def shadow(g, strength, r):
    h, w = g.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    a = r.uniform(0, 2 * np.pi)
    ramp = (np.cos(a) * xx / w + np.sin(a) * yy / h)
    ramp = (ramp - ramp.min()) / (ramp.max() - ramp.min())
    # soft blob = shadow of a hand or the phone
    cx, cy = r.uniform(0.2, 0.8) * w, r.uniform(0.2, 0.8) * h
    blob = np.exp(-(((xx - cx) / (0.35 * w)) ** 2 + ((yy - cy) / (0.25 * h)) ** 2))
    dark = np.clip(0.7 * ramp + 0.5 * blob, 0, 1) * strength
    return np.clip(g.astype(np.float32) * (1 - dark), 0, 255).astype(np.uint8)


def jpeg(g, q, r):
    ok, buf = cv2.imencode(".jpg", g, [cv2.IMWRITE_JPEG_QUALITY, int(q)])
    return cv2.imdecode(buf, cv2.IMREAD_GRAYSCALE)


def fax(g, scale, r):
    small = cv2.resize(g, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    bw = cv2.threshold(small, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    return cv2.resize(bw, (g.shape[1], g.shape[0]), interpolation=cv2.INTER_NEAREST)


DAMAGE = {"blur": blur, "noise": noise, "skew": skew, "shadow": shadow, "jpeg": jpeg, "fax": fax}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default="case01")
    args = ap.parse_args()

    case_dir = config.DATA_DIR / "cases" / args.case
    clean_dir = case_dir / "pages_clean"
    pages = sorted(clean_dir.glob("*.png"))
    if not pages:
        print(f"No clean pages in {clean_dir}. Run the case generator first.")
        return
    out_root = case_dir / "stress"
    r = np.random.default_rng(2026)
    manifest = {"case_id": args.case, "source": "pages_clean", "levels": LEVELS,
                "types": {t: {"description": DESCRIPTION[t], "settings": SETTINGS[t]} for t in DAMAGE},
                "answers": f"{args.case}_answers.json", "images": []}
    for kind, fn in DAMAGE.items():
        for level, setting in zip(LEVELS, SETTINGS[kind]):
            folder = out_root / kind / f"L{level}"
            folder.mkdir(parents=True, exist_ok=True)
            for p in pages:
                g = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
                out = folder / f"{p.stem}.jpg"
                cv2.imwrite(str(out), fn(g, setting, r), [cv2.IMWRITE_JPEG_QUALITY, 92])
                manifest["images"].append({"file": out.relative_to(case_dir).as_posix(), "type": kind,
                                           "level": level, "setting": setting, "source_page": p.name})
        print(f"  {kind:<7} L1-L4 done")
    (out_root / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"Wrote {len(manifest['images'])} images to {out_root}")


if __name__ == "__main__":
    main()
