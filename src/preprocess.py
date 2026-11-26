"""Image cleanup before OCR. This is where your imaging background shines.

Each step is a small function, so you can switch steps on and off and measure
how much each one helps (the ablation study for your pitch).
"""
from pathlib import Path

import cv2
import numpy as np

ALL_STEPS = ("gray", "denoise", "contrast", "upscale", "deskew")


def load_image(path: str | Path, page: int = 0, dpi: int = 300) -> np.ndarray:
    """Load a PNG/JPG, or render one page of a PDF. Returns a BGR image."""
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(str(path))
        pil = pdf[page].render(scale=dpi / 72).to_pil().convert("RGB")
        return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    img = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Could not read image: {path}")
    return img


def to_gray(img: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img


def denoise(gray: np.ndarray, strength: float = 10) -> np.ndarray:
    """Non-local means denoising: removes speckle/fax noise but keeps letter edges."""
    return cv2.fastNlMeansDenoising(gray, None, h=strength)


def enhance_contrast(gray: np.ndarray) -> np.ndarray:
    """CLAHE: local contrast boost, helps with faded or unevenly lit photos."""
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def estimate_skew(gray: np.ndarray, max_angle: float = 10.0, step: float = 0.25) -> float:
    """Find the rotation that makes text lines most horizontal.

    Tries angles and picks the one whose horizontal projection profile is
    sharpest (highest variance), the same idea as optimising a sharpness metric.
    """
    small = cv2.resize(gray, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
    binary = cv2.threshold(small, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    h, w = binary.shape
    center = (w / 2, h / 2)
    best_angle, best_score = 0.0, -1.0
    for angle in np.arange(-max_angle, max_angle + step, step):
        m = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(binary, m, (w, h), flags=cv2.INTER_NEAREST)
        score = float(np.var(rotated.sum(axis=1)))
        if score > best_score:
            best_angle, best_score = float(angle), score
    return best_angle


def deskew(gray: np.ndarray) -> tuple[np.ndarray, float]:
    angle = estimate_skew(gray)
    h, w = gray.shape
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    fixed = cv2.warpAffine(gray, m, (w, h), flags=cv2.INTER_CUBIC,
                           borderMode=cv2.BORDER_CONSTANT, borderValue=255)
    return fixed, angle


def estimate_noise(gray: np.ndarray) -> float:
    """Noise standard deviation (Immerkaer 1996, fast Laplacian-based estimate).

    Clean scans give about 0-2, phone photos 2-6, heavy noise 15+.
    """
    kernel = np.array([[1, -2, 1], [-2, 4, -2], [1, -2, 1]], dtype=float)
    h, w = gray.shape
    response = cv2.filter2D(gray.astype(float), -1, kernel)[1:-1, 1:-1]
    return float(np.abs(response).sum() * np.sqrt(0.5 * np.pi) / (6 * (w - 2) * (h - 2)))


def upscale(gray: np.ndarray, factor: float = 2.0) -> np.ndarray:
    """Bigger letters help OCR on low-resolution images (fax, small photos)."""
    return cv2.resize(gray, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)


# Tuned on the synthetic robustness set (see run_evaluation.py)
NOISE_SKIP = 3.0        # below this sigma: image is clean, don't denoise
NOISE_NO_CONTRAST = 5.0  # above this sigma: CLAHE amplifies noise, skip it
UPSCALE_BELOW = 3000     # upscale 2x if the page is shorter than this (in pixels)


def preprocess(img: np.ndarray, steps=ALL_STEPS) -> tuple[np.ndarray, list[str]]:
    """Run the chosen cleanup steps in order. Returns the image and a log.

    Adaptive: each step first measures the image and only acts when it helps.
    v1 lesson: a fixed denoise + contrast boost destroyed noisy pages, because
    CLAHE re-amplified the leftover noise.
    """
    log = []
    out = to_gray(img)
    log.append("gray")
    sigma = estimate_noise(out)
    log.append(f"noise sigma {sigma:.1f}")
    if "denoise" in steps:
        if sigma >= NOISE_SKIP:
            strength = max(10.0, 0.9 * sigma)
            out = denoise(out, strength=strength)
            log.append(f"denoise (h={strength:.0f})")
        else:
            log.append("denoise skipped (clean)")
    if "contrast" in steps:
        if sigma < NOISE_NO_CONTRAST:
            out = enhance_contrast(out)
            log.append("contrast")
        else:
            log.append("contrast skipped (noisy)")
    if "upscale" in steps and out.shape[0] < UPSCALE_BELOW:
        out = upscale(out)
        log.append("upscale 2x")
    if "deskew" in steps:
        out, angle = deskew(out)
        log.append(f"deskew ({angle:+.2f} deg)")
    return out, log