r"""Stress set B: case01_hard = the same patient and the same 20 pages, but harder documents.

What changes compared with case01 (also written to case01_hard/manifest.json):

  LAYOUT
  p04  Medication plan in LANDSCAPE (like the real German Bundeseinheitlicher Medikationsplan),
       and photographed sideways (phone held upright): text runs 90° rotated
  p06  Lab report as a CUMULATIVE table turned on its side: dates are rows, lab values are
       columns (horizontal instead of vertical), three dates
  p09  Echo table WITHOUT grid lines (values only aligned by spacing)

  HANDWRITING (blue pen, added on top of the printed page)
  p01  "!!" and underline next to the heart failure diagnosis           (noise, no new fact)
  p03  Glimepirid row STRUCK THROUGH + margin note "abgesetzt 20.11."   (confirms the fax)
  p04  "ALT! siehe Entlassbrief" written across the top                (noise, helpful hint)
  p07  Side note on the referral: "Ramipril pausiert seit 20.11. (Schwindel)"   -> NEW fact N14
  p13  Signature scribble on the signature line                        (noise)
  p14  "keine bekannt" STRUCK THROUGH, "Penicillin!" written next to it -> conflict C5 changes

Ground truth: case01_hard_answers.json (copy of case01 with the changes above, every needle
has its own match words). Photos: pages_photo/ like case01.

Run:   python scripts\make_hard_case.py          (needs case01 to exist: scripts\generate_case.py)
Then:  python scripts\process_case.py --pages data\cases\case01_hard\pages_photo
"""
import copy
import importlib.util
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Frame, Spacer, Table, TableStyle

from src import config

# reuse the case01 generator (pages, styles, helpers, ground truth)
_spec = importlib.util.spec_from_file_location("generate_case", ROOT / "scripts" / "generate_case.py")
gc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gc)

CASE = "case01_hard"
OUT = config.DATA_DIR / "cases" / CASE
DPI = 200
INK = 70                       # pen colour in the grey page (0 = black, 255 = white)
rng = np.random.default_rng(42)

# ------------------------------------------------------------------ new layouts

def p04_landscape(c):
    """Medication plan in landscape A4, same content as case01 page 4."""
    LW, LH = landscape(A4)
    c.setPageSize((LW, LH))
    c.setFont("Helvetica-Bold", 15)
    c.drawString(15 * mm, LH - 16 * mm, "Medikationsplan")
    c.setFont("Helvetica", 9)
    c.drawString(15 * mm, LH - 22 * mm, f"für: {gc.PATIENT['name']}   geb. am: {gc.PATIENT['birth']}   (FIKTIV)")
    c.drawString(15 * mm, LH - 27 * mm, "ausgedruckt von: Dr. med. A. Hausmann, Am Markt 3, 80002 Musterstadt"
                                       "   ·   ausgedruckt am: 02.09.2026")
    c.rect(LW - 40 * mm, LH - 36 * mm, 25 * mm, 25 * mm)
    c.setFont("Helvetica", 6)
    c.drawCentredString(LW - 27.5 * mm, LH - 24 * mm, "[2D-Code]")
    rows = [["Wirkstoff", "Handelsname", "Stärke", "Form", "Mo", "Mi", "Ab", "zN", "Einheit", "Hinweise", "Grund"],
            ["Phenprocoumon", "Marcumar", "3 mg", "Tabl", "", "", "nach INR", "", "Stück", "INR-Ziel 2-3", "Blutverdünnung"],
            ["Bisoprolol", "Bisoprolol", "2,5 mg", "Tabl", "1", "0", "0", "0", "Stück", "", "Herz"],
            ["Ramipril", "Ramipril", "2,5 mg", "Tabl", "1", "0", "0", "0", "Stück", "", "Blutdruck"],
            ["Torasemid", "Torem", "10 mg", "Tabl", "1", "0", "0", "0", "Stück", "morgens", "Wasser"],
            ["Metformin", "Metformin", "1000 mg", "Tabl", "1", "0", "1", "0", "Stück", "zum Essen", "Diabetes"],
            ["Glimepirid", "Amaryl", "1 mg", "Tabl", "1", "0", "0", "0", "Stück", "vor dem Frühstück", "Diabetes"],
            ["Atorvastatin", "Sortis", "20 mg", "Tabl", "0", "0", "1", "0", "Stück", "", "Cholesterin"],
            ["Pantoprazol", "Pantozol", "20 mg", "Tabl", "1", "0", "0", "0", "Stück", "", "Magen"]]
    t = gc.table(rows, [30, 25, 17, 12, 9, 9, 16, 9, 15, 38, 34])
    f = Frame(15 * mm, 20 * mm, LW - 30 * mm, LH - 62 * mm, leftPadding=0, rightPadding=0,
              topPadding=0, bottomPadding=0)
    f.addFromList([t, Spacer(1, 4 * mm),
                   gc.P("Bitte bringen Sie diesen Plan zu jedem Arzt- und Apothekenbesuch mit.", gc.SMALL)], c)
    c.setFont("Helvetica", 7.5)
    c.drawString(15 * mm, 10 * mm, f"{gc.PAT_LINE}   ·   FIKTIVE DATEN – nur für Test- und Demozwecke")
    c.drawRightString(LW - 15 * mm, 10 * mm, "Seite 1 von 1")


def p06_horizontal(c):
    """Cumulative lab report: one ROW per date, one COLUMN per lab value (transposed table)."""
    gc.header(c, *gc.LABOR)
    head = ["Datum", "Na", "K", "Krea", "eGFR", "Harn-\nstoff", "Hb", "Leuko", "CRP", "NT-\nproBNP", "TSH"]
    units = ["", "mmol/l", "mmol/l", "mg/dl", "ml/min", "mg/dl", "g/dl", "/nl", "mg/l", "pg/ml", "mU/l"]
    ref = ["Ref.", "136-145", "3,5-5,1", "0,5-0,9", "> 60", "17-43", "12-15,5", "3,9-10,2", "< 5", "< 450", "0,27-4,2"]
    rows = [head, units, ref,
            ["06.10.2026", "137", "4,8", "1,6 H", "32 L", "68 H", "11,9 L", "7,1", "6 H", "2840 H", "–"],
            ["04.11.2026", "136", "5,0", "1,7 H", "30 L", "74 H", "11,5 L", "6,9", "5", "3310 H", "–"],
            ["18.11.2026", "135 L", "5,3 H", "1,9 H", "28 L", "81 H", "11,2 L", "6,8", "4", "4120 H", "2,1"]]
    t = Table(rows, colWidths=[22 * mm] + [14.8 * mm] * 10)
    t.setStyle(TableStyle([("FONT", (0, 0), (-1, -1), "Helvetica", 8),
                           ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8),
                           ("FONT", (0, 1), (-1, 2), "Helvetica", 6.5),
                           ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#777777")),
                           ("BACKGROUND", (0, 0), (-1, 2), colors.HexColor("#E6E6E6")),
                           ("ALIGN", (1, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    gc.flow(c, [
        gc.P("Kumulativbefund Labor", gc.H1),
        gc.P(f"{gc.PAT_LINE}<br/>Einsender: Hausarztpraxis Dr. med. A. Hausmann · Befunddatum: 18.11.2026", gc.BODY),
        Spacer(1, 4 * mm), t, Spacer(1, 4 * mm),
        gc.P("H = oberhalb, L = unterhalb des Referenzbereichs. eGFR nach CKD-EPI. Neuester Wert unten.", gc.SMALL),
        Spacer(1, 6 * mm),
        gc.P("Technisch und medizinisch freigegeben: Dr. med. M. Probe (fiktiv)", gc.SMALL),
    ])
    gc.footer(c, "Seite 1 von 1")


def p09_no_lines(c):
    """Echo report, table drawn WITHOUT grid lines."""
    gc.header(c, *gc.KARDIO)
    rows = [["Messung", "Wert", "Norm"], ["LVEF (biplan, Simpson)", "40 %", "> 52 %"],
            ["LVEDD", "56 mm", "< 53 mm"], ["Linker Vorhof (Volumen)", "48 ml/m²", "< 34 ml/m²"],
            ["TAPSE", "16 mm", "> 17 mm"], ["sPAP (geschätzt)", "48 mmHg", "< 35 mmHg"]]
    t = Table(rows, colWidths=[70 * mm, 40 * mm, 40 * mm])
    t.setStyle(TableStyle([("FONT", (0, 0), (-1, -1), "Helvetica", 9),
                           ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9)]))
    gc.flow(c, [
        gc.P("Transthorakale Echokardiographie", gc.H1),
        gc.P(f"{gc.PAT_LINE} · 12.10.2026 · Rhythmus: Vorhofflimmern", gc.BODY), Spacer(1, 3 * mm),
        t, Spacer(1, 3 * mm),
        gc.P("<b>Befund:</b> Leicht dilatierter linker Ventrikel mit global leicht- bis mittelgradig eingeschränkter "
             "systolischer Funktion. Mitralklappeninsuffizienz Grad II, Trikuspidalinsuffizienz Grad I. "
             "Schrittmachersonde im rechten Ventrikel. Kein Perikarderguss.", gc.BODY),
        gc.P("<b>Beurteilung:</b> Herzinsuffizienz mit leicht reduzierter Pumpfunktion (HFmrEF), LVEF 40 %. "
             "Pulmonale Hypertonie wahrscheinlich.", gc.BODY),
        Spacer(1, 6 * mm), gc.P("Dr. med. J. Puls (fiktiv)", gc.BODY),
    ])
    gc.footer(c, "Seite 1 von 1")


def pages():
    out = list(gc.PAGES)
    out[3], out[5], out[8] = p04_landscape, p06_horizontal, p09_no_lines
    return out

# ------------------------------------------------------------------ handwriting on the page image

FONT_CANDIDATES = [  # Windows handwriting-like fonts first, then a fallback that exists everywhere
    r"C:\Windows\Fonts\Inkfree.ttf", r"C:\Windows\Fonts\segoepr.ttf", r"C:\Windows\Fonts\segoesc.ttf",
    r"C:\Windows\Fonts\comic.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
]


def hand_font(size):
    for f in FONT_CANDIDATES:
        if Path(f).exists():
            return ImageFont.truetype(f, size), Path(f).name
    return ImageFont.load_default(), "default"


def write(draw_img: Image.Image, x, y, text, size=46):
    """Pen writing: every letter slightly rotated, resized and shifted, like a real hand."""
    cx = x
    for ch in text:
        s = int(size * rng.uniform(0.92, 1.08))
        f, _ = hand_font(s)
        if not ch.strip():
            cx += s * 0.35
            continue
        box = f.getbbox(ch)
        side = int(s * 1.8)
        glyph = Image.new("L", (side, side), 0)
        # same baseline for every letter: draw at a fixed anchor, rotate around the centre
        ImageDraw.Draw(glyph).text((side // 4, side // 4), ch, font=f, fill=255)
        glyph = glyph.rotate(rng.uniform(-7, 7), resample=Image.BICUBIC, center=(side // 4 + box[2] // 2, side // 2))
        ink = Image.new("L", glyph.size, INK)
        draw_img.paste(ink, (int(cx - side // 4), int(y - side // 4 + rng.uniform(-2.5, 2.5))), glyph)
        cx += (box[2] - box[0]) * rng.uniform(0.97, 1.06) + 3
    return cx


def pen_line(draw: ImageDraw.ImageDraw, x0, y0, x1, y1, width=5, wobble=4):
    n = max(int(abs(x1 - x0) / 25), 4)
    pts = [(x0 + (x1 - x0) * i / n + rng.uniform(-2, 2),
            y0 + (y1 - y0) * i / n + rng.uniform(-wobble, wobble)) for i in range(n + 1)]
    draw.line(pts, fill=INK, width=width, joint="curve")


def strike(draw, box):
    x0, y0, x1, y1 = box
    ym = (y0 + y1) / 2
    pen_line(draw, x0 - 12, ym + 3, x1 + 12, ym - 3)
    pen_line(draw, x0 - 8, ym - 5, x1 + 8, ym + 6, width=4)


def underline(draw, box):
    x0, y0, x1, y1 = box
    pen_line(draw, x0, y1 + 6, x1, y1 + 10, width=4)


def scribble(draw, x, y, w=320):
    pts, cx = [], x
    while cx < x + w:
        pts.append((cx, y + rng.uniform(-28, 10)))
        cx += rng.uniform(10, 26)
    draw.line(pts, fill=INK, width=4, joint="curve")


def find(gray: np.ndarray, words: list[str], whole_line=False):
    """Locate printed words on the clean page with Tesseract (clean pages read perfectly).

    Returns the pixel box of the first line that contains all words, either just the
    words or the whole row (for striking through a table row)."""
    import pytesseract
    if config.TESSERACT_CMD and Path(config.TESSERACT_CMD).exists():
        pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD
    d = pytesseract.image_to_data(gray, lang="deu", output_type=pytesseract.Output.DICT)
    rows = {}
    for i, t in enumerate(d["text"]):
        if t.strip():
            rows.setdefault((d["block_num"][i], d["par_num"][i], d["line_num"][i]), []).append(i)
    # table cells end up in separate blocks: also group by y position
    by_y = {}
    for i, t in enumerate(d["text"]):
        if t.strip():
            by_y.setdefault(round((d["top"][i] + d["height"][i] / 2) / 18), []).append(i)
    groups = list(by_y.values()) + list(rows.values()) if whole_line else list(rows.values()) + list(by_y.values())
    for group in groups:
        text = " ".join(d["text"][i] for i in group).lower()
        if all(w.lower() in text for w in words):
            hits = group if whole_line else [i for i in group if any(w.lower() in d["text"][i].lower() for w in words)]
            x0 = min(d["left"][i] for i in hits)
            y0 = min(d["top"][i] for i in hits)
            x1 = max(d["left"][i] + d["width"][i] for i in hits)
            y1 = max(d["top"][i] + d["height"][i] for i in hits)
            return x0, y0, x1, y1
    raise LookupError(f"could not find {words} on the page")


def annotate(page_no: int, gray: np.ndarray) -> tuple[np.ndarray, list[dict]]:
    img = Image.fromarray(gray)
    draw = ImageDraw.Draw(img)
    done = []
    W = gray.shape[1]
    if page_no == 1:
        b = find(gray, ["Akut", "dekompensierte"])
        underline(draw, b)
        write(img, 30, b[1] - 10, "!!", 52)
        done.append({"kind": "underline + '!!'", "where": "diagnosis 1", "changes_truth": False})
    elif page_no == 3:
        b = find(gray, ["Glimepirid"], whole_line=True)
        strike(draw, b)
        write(img, b[2] + 260, b[1] - 6, "abgesetzt 20.11.", 40)
        done.append({"kind": "strike-through row + note", "where": "Glimepirid row",
                     "text": "abgesetzt 20.11.", "changes_truth": False, "note": "confirms the fax (p19)"})
    elif page_no == 4:   # landscape page (wider than tall)
        write(img, int(W * 0.40), 40, "ALT! siehe Entlassbrief", 54)
        done.append({"kind": "note across the top", "text": "ALT! siehe Entlassbrief", "changes_truth": False})
    elif page_no == 7:
        b = find(gray, ["Aktuelle", "Medikation"])
        y = b[3] + 150
        x = write(img, b[0] + 40, y, "Ramipril pausiert seit 20.11.", 46)
        write(img, b[0] + 40, y + 62, "(Schwindel)  - Hausmann", 46)
        pen_line(draw, b[0] + 10, y + 10, b[0] + 30, y + 30, width=4)
        done.append({"kind": "side note", "text": "Ramipril pausiert seit 20.11. (Schwindel)",
                     "changes_truth": True, "note": "new fact N14, new conflict C6"})
    elif page_no == 13:
        b = find(gray, ["Unterschrift"])
        scribble(draw, b[2] + 40, b[3] - 4)
        done.append({"kind": "signature scribble", "changes_truth": False})
    elif page_no == 14:
        b = find(gray, ["keine", "bekannt"])
        strike(draw, b)
        write(img, b[2] + 30, b[1] - 12, "Penicillin!", 48)
        done.append({"kind": "strike-through + correction", "where": "Allergien",
                     "text": "keine bekannt -> Penicillin!", "changes_truth": True, "note": "conflict C5 changes"})
    return np.array(img), done

# ------------------------------------------------------------------ ground truth

def make_answers(base: dict) -> dict:
    a = copy.deepcopy(base)
    a["case_id"] = CASE
    a["variant_of"] = "case01"
    for m in a["current_medication"]:
        if m["name"] == "Ramipril":
            m.update(status="paused", sources=[3, 4, 7],
                     note="laut handschriftlicher Notiz auf der Einweisung seit 20.11. pausiert (Schwindel)")
    for c in a["conflicts"]:
        if c["id"] == "C5":
            c["text"] = ("Pflegeüberleitung: gedruckt 'Allergien: keine bekannt', handschriftlich durchgestrichen "
                         "und zu 'Penicillin!' korrigiert; Arztbrief 2022: Penicillin-Allergie.")
    a["conflicts"].append({"id": "C6", "text": "Ramipril laut Entlassungsbrief aktiv, laut handschriftlicher "
                                               "Notiz auf der Einweisung seit 20.11. pausiert.", "sources": [3, 7]})
    a["needles"].append({"id": "N14", "category": "Medikation",
                         "fact": "Ramipril seit 20.11. pausiert (Schwindel), nur handschriftlich auf der Einweisung",
                         "sources": [7]})
    for t in a["traps"]:
        if t["id"] == "T4":
            t["text"] = "Pflegebogen: gedrucktes 'keine bekannt' ist durchgestrichen, gilt nicht"
    a["traps"].append({"id": "T5", "text": "Kumulativbefund (S. 6): neuester Wert ist die UNTERSTE Zeile (18.11.)",
                       "sources": [6]})
    a["traps"].append({"id": "T6", "text": "Medikationsplan (S. 4) liegt quer und ist hochkant fotografiert",
                       "sources": [4]})
    return a

# ------------------------------------------------------------------ main

def main():
    import pypdfium2 as pdfium

    base_answers = gc.OUT / "case01_answers.json"
    if not base_answers.exists():
        print("case01 not found, creating it first ...")
        gc.main()
    for sub in ("pages_clean", "pages_photo"):
        (OUT / sub).mkdir(parents=True, exist_ok=True)

    pdf_path = OUT / f"{CASE}_all.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    c.setTitle(f"{CASE} – fiktiver Notaufnahme-Fall, schwierige Dokumente (FIKTIVE DATEN)")
    for fn in pages():
        c.setPageSize(A4)
        fn(c)
        c.showPage()
    c.save()

    r = np.random.default_rng(11)
    pdf = pdfium.PdfDocument(str(pdf_path))
    manifest = {"case_id": CASE, "variant_of": "case01", "fictional": True,
                "handwriting_font": hand_font(40)[1], "pages": []}
    layout_notes = {4: "landscape A4, photographed rotated 90°", 6: "cumulative lab table, dates as rows (transposed)",
                    9: "table without grid lines"}
    clean = []
    for i in range(len(pdf)):
        page = i + 1
        g = np.array(pdf[i].render(scale=DPI / 72).to_pil().convert("L"))
        g, notes = annotate(page, g)
        if i == 18:
            g = gc.fax_look(g)
        clean.append(g)
        cv2.imwrite(str(OUT / "pages_clean" / f"{CASE}_p{page:02d}.png"), g)
        photo_src = cv2.rotate(g, cv2.ROTATE_90_CLOCKWISE) if page == 4 else g
        cv2.imwrite(str(OUT / "pages_photo" / f"{CASE}_p{page:02d}.jpg"), gc.photo_like(photo_src, r))
        manifest["pages"].append({"page": page, "layout": layout_notes.get(page, "as case01"),
                                  "handwriting": notes})
        print(f"  page {page:2d}  {layout_notes.get(page, '')}  {', '.join(n['kind'] for n in notes)}")
    blurry = gc.photo_like(cv2.rotate(clean[3], cv2.ROTATE_90_CLOCKWISE), r, strong=True)
    cv2.imwrite(str(OUT / "pages_clean" / f"{CASE}_p20.png"), blurry)
    cv2.imwrite(str(OUT / "pages_photo" / f"{CASE}_p20.jpg"), blurry)
    manifest["pages"].append({"page": 20, "layout": "blurry re-photo of page 4 (duplicate)", "handwriting": []})

    answers = make_answers(json.loads(base_answers.read_text(encoding="utf-8")))
    (OUT / f"{CASE}_answers.json").write_text(json.dumps(answers, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Created {CASE}: 20 pages, answers with {len(answers['needles'])} needles, manifest.json")


if __name__ == "__main__":
    main()
