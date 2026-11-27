"""Shared UI building blocks for the Streamlit views.

Kept separate from src/ on purpose: src/ is the pipeline and must never import
Streamlit, so the same code can sit behind the FastAPI backend later.
"""
from __future__ import annotations

import html
import io
import json
from pathlib import Path

import cv2
import numpy as np
import streamlit as st
from PIL import Image

from src import config
from src.preprocess import load_image, preprocess

# ------------------------------------------------------------------ look and feel

DOC_TYPE_LABELS = {
    "discharge_letter": "Arztbrief", "medication_plan": "Medikationsplan", "lab_report": "Labor",
    "referral": "Einweisung", "imaging_report": "Bildgebung", "surgery_report": "OP-Bericht",
    "advance_directive": "Patientenverfügung", "nursing_transfer": "Pflegeüberleitung",
    "fax_note": "Fax / Notiz", "specialist_letter": "Facharztbrief", "other_medical": "Sonstiges",
    "irrelevant": "Nicht relevant", "unknown": "Unklar", None: "–",
}
DOC_TYPE_COLORS = {
    "discharge_letter": "#2563eb", "medication_plan": "#7c3aed", "lab_report": "#0891b2",
    "referral": "#0d9488", "imaging_report": "#4f46e5", "surgery_report": "#9333ea",
    "advance_directive": "#be123c", "nursing_transfer": "#c2410c", "fax_note": "#a16207",
    "specialist_letter": "#0369a1", "other_medical": "#64748b", "irrelevant": "#94a3b8", "unknown": "#94a3b8",
}
STATUS_LABELS = {"active": "aktiv", "new": "neu", "paused": "pausiert", "stopped": "abgesetzt"}
FACT_COLORS_BGR = {  # highlight colours on the page image (OpenCV uses BGR)
    "meds": (235, 99, 37), "diagnoses": (92, 81, 225), "labs": (178, 145, 8),
    "cave": (60, 20, 220), "contacts": (60, 130, 13), "findings": (180, 60, 150), "negatives": (120, 120, 120),
}
FACT_LABELS = {"meds": "Medikation", "diagnoses": "Diagnose", "labs": "Labor", "cave": "CAVE",
               "contacts": "Kontakt", "findings": "Befund", "negatives": "Negativbefund"}

CSS = """
<style>
.block-container {padding-top: 3.2rem; padding-bottom: 3rem; max-width: 1400px;}
h1, h2, h3 {letter-spacing: -0.01em;}
.gw-header {display:flex; align-items:center; justify-content:space-between; gap:1rem;
            padding: .9rem 1.1rem; border:1px solid #e2e8f0; border-radius:14px; background:#f8fafc;
            margin-bottom: .8rem;}
.gw-header .name {font-size:1.35rem; font-weight:700; color:#0f172a;}
.gw-header .meta {color:#475569; font-size:.92rem;}
.gw-chip {display:inline-block; padding:.12rem .5rem; margin:0 .25rem .25rem 0; border-radius:999px;
          font-size:.76rem; font-weight:600; background:#e2e8f0; color:#334155; white-space:nowrap;}
.gw-src {display:inline-block; padding:.02rem .38rem; margin-left:.2rem; border-radius:6px; font-size:.72rem;
         font-weight:600; background:#eef2ff; color:#3730a3; border:1px solid #c7d2fe; white-space:nowrap;}
.gw-card {border-radius:12px; padding:.85rem 1rem; margin-bottom:.7rem; border:1px solid;}
.gw-card h4 {margin:0 0 .45rem 0; font-size:.95rem; letter-spacing:.02em; text-transform:uppercase;}
.gw-card ul {margin:0; padding-left:1.1rem;}
.gw-card li {margin:.18rem 0; line-height:1.45;}
.gw-cave {background:#fef2f2; border-color:#fecaca;} .gw-cave h4 {color:#b91c1c;}
.gw-warn {background:#fffbeb; border-color:#fde68a;} .gw-warn h4 {color:#b45309;}
.gw-info {background:#f8fafc; border-color:#e2e8f0;} .gw-info h4 {color:#334155;}
.gw-ok {background:#f0fdf4; border-color:#bbf7d0;} .gw-ok h4 {color:#15803d;}
.gw-thumbcap {font-size:.78rem; line-height:1.3; margin-top:.15rem;}
.gw-badge {display:inline-block; padding:.05rem .4rem; border-radius:6px; font-size:.7rem; font-weight:700;
           color:white;}
.gw-muted {color:#64748b; font-size:.85rem;}
.gw-conflict {padding:.5rem .75rem; border-left:4px solid #f59e0b; background:#fffbeb; border-radius:6px;
              font-size:.92rem; line-height:1.45;}
.gw-conflict.done {border-left-color:#16a34a; background:#f0fdf4; color:#64748b;}
@media (prefers-color-scheme: dark) {
  .gw-header {background:#0f172a; border-color:#334155;} .gw-header .name {color:#f1f5f9;}
  .gw-header .meta, .gw-muted {color:#94a3b8;}
  .gw-chip {background:#334155; color:#e2e8f0;}
  .gw-src {background:#1e1b4b; color:#c7d2fe; border-color:#3730a3;}
  .gw-conflict {background:#2a2010;} .gw-conflict.done {background:#0c1f14;}
  .gw-cave {background:#2a1215;} .gw-warn {background:#2a2010;} .gw-info {background:#0f172a;} .gw-ok {background:#0c1f14;}
}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def esc(text) -> str:
    return html.escape(str(text if text is not None else ""))


def chip(text, color: str | None = None) -> str:
    style = f' style="background:{color};color:white"' if color else ""
    return f'<span class="gw-chip"{style}>{esc(text)}</span>'


def doc_chip(doc_type) -> str:
    return chip(DOC_TYPE_LABELS.get(doc_type, doc_type), DOC_TYPE_COLORS.get(doc_type, "#64748b"))


def sources(pages) -> str:
    return "".join(f'<span class="gw-src">S.&nbsp;{esc(p)}</span>' for p in pages or [])


def card(title: str, items: list[str], kind: str = "info", empty: str = "Keine Angaben gefunden.") -> str:
    """items are already-escaped HTML snippets."""
    body = "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>" if items else f'<span class="gw-muted">{esc(empty)}</span>'
    return f'<div class="gw-card gw-{kind}"><h4>{esc(title)}</h4>{body}</div>'


def html_block(markup: str):
    st.markdown(markup, unsafe_allow_html=True)

# ------------------------------------------------------------------ images (cached)

@st.cache_data(show_spinner=False, max_entries=400)
def thumbnail(path: str, mtime: float, width: int = 360) -> bytes:
    img = Image.open(path)
    img.thumbnail((width, width * 2))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=80)
    return buf.getvalue()


@st.cache_data(show_spinner="Seite wird aufbereitet …", max_entries=60)
def cleaned_page(path: str, mtime: float) -> tuple[np.ndarray, list[str]]:
    return preprocess(load_image(path))


def highlight(clean: np.ndarray, lines: list[dict], facts: list[dict]) -> np.ndarray:
    """Draw boxes around the OCR lines that facts came from, coloured by fact type."""
    out = cv2.cvtColor(clean, cv2.COLOR_GRAY2BGR) if clean.ndim == 2 else clean.copy()
    h, w = out.shape[:2]
    by_text = {}
    for f in facts:
        if f.get("source_text"):
            by_text.setdefault(f["source_text"], f["kind"])
    pad = max(4, w // 300)
    for line in lines:
        kind = by_text.get(line["text"])
        if not kind or not line.get("bbox"):
            continue
        b = line["bbox"]
        p0 = (max(int(b["x0"] * w) - pad, 0), max(int(b["y0"] * h) - pad, 0))
        p1 = (min(int(b["x1"] * w) + pad, w - 1), min(int(b["y1"] * h) + pad, h - 1))
        overlay = out.copy()
        cv2.rectangle(overlay, p0, p1, FACT_COLORS_BGR.get(kind, (0, 0, 255)), -1)
        out = cv2.addWeighted(overlay, 0.18, out, 0.82, 0)
        cv2.rectangle(out, p0, p1, FACT_COLORS_BGR.get(kind, (0, 0, 255)), max(2, w // 600))
    return cv2.cvtColor(out, cv2.COLOR_BGR2RGB)


def ocr_cache(out_dir: Path, file_name: str, engine: str) -> dict | None:
    f = out_dir / "ocr" / f"{Path(file_name).stem}_{engine}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def legend() -> str:
    def hexcol(bgr):
        return "#%02x%02x%02x" % (bgr[2], bgr[1], bgr[0])
    return "".join(chip(FACT_LABELS[k], hexcol(c)) for k, c in FACT_COLORS_BGR.items() if k != "negatives")
