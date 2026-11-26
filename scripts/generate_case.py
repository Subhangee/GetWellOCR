r"""Fictional multi-document ER case: 20 pages of German medical documents.

Creates, in data/cases/case01/:
  case01_all.pdf          all 20 pages (to print or view)
  pages_clean/            one PNG per page (perfect scans)
  pages_photo/            one JPG per page, degraded like phone photos
  case01_answers.json     ground truth: documents, current medication,
                          conflicts and the 13 "needles" the ER summary must find
  case01_mock_api.json    the same, shaped as the app's case-summary response
                          (frontend can build against it before the API exists)

Run:   python scripts\generate_case.py
ALL DATA IS FICTIONAL.
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2
import numpy as np
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Frame, Paragraph, Spacer, Table, TableStyle

from src import config

OUT = config.DATA_DIR / "cases" / "case01"
W, H = A4
rng = random.Random(7)

PATIENT = {"name": "Helga Beispiel", "birth": "14.03.1948", "age": 78, "sex": "w",
           "address": "Musterweg 12, 80000 Musterstadt", "insurance": "Muster-Krankenkasse"}
PAT_LINE = f"Pat.: {PATIENT['name']}, geb. {PATIENT['birth']} (FIKTIV)"

BODY = ParagraphStyle("b", fontName="Helvetica", fontSize=10, leading=13.5)
BOLD = ParagraphStyle("bb", parent=BODY, fontName="Helvetica-Bold")
H1 = ParagraphStyle("h1", parent=BODY, fontName="Helvetica-Bold", fontSize=14, leading=18, spaceAfter=4)
H2 = ParagraphStyle("h2", parent=BODY, fontName="Helvetica-Bold", fontSize=11, leading=15, spaceBefore=8, spaceAfter=2)
SMALL = ParagraphStyle("s", parent=BODY, fontSize=8.5, leading=11, textColor=colors.HexColor("#333333"))


# ------------------------------------------------------------ page helpers

def header(c, inst, sub, addr):
    c.setFont("Helvetica-Bold", 13)
    c.drawString(20 * mm, H - 18 * mm, inst)
    c.setFont("Helvetica", 8.5)
    c.drawString(20 * mm, H - 23 * mm, sub)
    c.drawString(20 * mm, H - 27 * mm, addr)
    c.setLineWidth(0.6)
    c.line(20 * mm, H - 30 * mm, W - 20 * mm, H - 30 * mm)


def footer(c, page_label):
    c.setFont("Helvetica", 7.5)
    c.drawString(20 * mm, 12 * mm, f"{PAT_LINE}   ·   FIKTIVE DATEN – nur für Test- und Demozwecke")
    c.drawRightString(W - 20 * mm, 12 * mm, page_label)


def flow(c, items, top=H - 36 * mm, bottom=18 * mm):
    f = Frame(20 * mm, bottom, W - 40 * mm, top - bottom, leftPadding=0, rightPadding=0,
              topPadding=0, bottomPadding=0, showBoundary=0)
    rest = f.addFromList(list(items), c)
    if rest:
        raise ValueError(f"Page overflow: {len(rest)} item(s) did not fit")


def P(text, style=BODY):
    return Paragraph(text, style)


def table(rows, widths, head=True):
    t = Table(rows, colWidths=[w * mm for w in widths])
    style = [("FONT", (0, 0), (-1, -1), "Helvetica", 9),
             ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#777777")),
             ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if head:
        style += [("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
                  ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6E6E6"))]
    t.setStyle(TableStyle(style))
    return t


def handwriting(c, x, y, text, size=15, color=(0.1, 0.15, 0.55)):
    """Fake handwriting: oblique font, per-letter jitter in position, size and angle."""
    c.setFillColorRGB(*color)
    cx = x
    for ch in text:
        s = size * rng.uniform(0.9, 1.12)
        c.saveState()
        c.translate(cx, y + rng.uniform(-1.4, 1.4))
        c.rotate(rng.uniform(-6, 6))
        c.setFont("Helvetica-Oblique", s)
        c.drawString(0, 0, ch)
        c.restoreState()
        cx += c.stringWidth(ch, "Helvetica-Oblique", s) * rng.uniform(0.95, 1.08)
    c.setFillColorRGB(0, 0, 0)
    return cx


KARDIO = ("Klinikum Musterstadt – Medizinische Klinik II, Kardiologie",
          "Chefarzt Prof. Dr. med. F. Herzog (fiktiv)", "Klinikstraße 1, 80001 Musterstadt · Tel. 089 000000-0")
HAUSARZT = ("Hausarztpraxis Dr. med. A. Hausmann (fiktiv)", "Fachärztin für Allgemeinmedizin",
            "Am Markt 3, 80002 Musterstadt · Tel. 089 000000-1 · Fax 089 000000-2")
LABOR = ("MVZ Labor Musterstadt (fiktiv)", "Laboratoriumsmedizin", "Laborweg 5, 80003 Musterstadt")
RADIO = ("Klinikum Musterstadt – Institut für Radiologie", "Direktor Prof. Dr. med. R. Strahl (fiktiv)",
         "Klinikstraße 1, 80001 Musterstadt")
ORTHO = ("Klinikum Musterstadt – Klinik für Orthopädie und Unfallchirurgie", "Chefarzt Dr. med. K. Knochen (fiktiv)",
         "Klinikstraße 1, 80001 Musterstadt")
INNERE = ("Kreisklinik Beispielhausen – Innere Medizin", "Chefärztin Dr. med. L. Lunge (fiktiv)",
          "Krankenhausweg 7, 80010 Beispielhausen")
DIABETO = ("Diabetologische Schwerpunktpraxis Dr. med. Z. Zucker (fiktiv)", "Diabetologie DDG",
           "Süßgasse 9, 80004 Musterstadt")


# ------------------------------------------------------------ the 20 pages

def p01(c):
    header(c, *KARDIO)
    flow(c, [
        P("Hausarztpraxis Dr. med. A. Hausmann · Am Markt 3 · 80002 Musterstadt", SMALL), Spacer(1, 6 * mm),
        P("Musterstadt, 14.10.2026", BODY), Spacer(1, 3 * mm),
        P("Entlassungsbrief", H1),
        P(f"<b>{PATIENT['name']}</b>, geb. {PATIENT['birth']}, {PATIENT['address']}", BODY),
        P("Stationärer Aufenthalt vom 06.10.2026 bis 14.10.2026", BODY), Spacer(1, 3 * mm),
        P("Sehr geehrte Frau Kollegin Dr. Hausmann,", BODY),
        P("wir berichten über Ihre gemeinsame Patientin, die sich vom 06.10.2026 bis 14.10.2026 in unserer "
          "stationären Behandlung befand.", BODY),
        P("Diagnosen", H2),
        P("1. Akut dekompensierte Herzinsuffizienz mit leicht reduzierter Ejektionsfraktion (HFmrEF, LVEF 40 %) (I50.13)<br/>"
          "2. Permanentes Vorhofflimmern, CHA2DS2-VASc-Score 6 (I48.2)<br/>"
          "3. Chronische Niereninsuffizienz Stadium G4 (N18.4)<br/>"
          "4. Diabetes mellitus Typ 2, nicht insulinpflichtig (E11.90)<br/>"
          "5. Arterielle Hypertonie (I10.90)<br/>"
          "6. Mitralklappeninsuffizienz Grad II (I34.0)", BODY),
        P("Nebendiagnosen / Vorgeschichte", H2),
        P("Z.n. Hüft-TEP rechts 03/2023 · Z.n. Schrittmacherimplantation (VVI) 2019 bei Bradyarrhythmia absoluta · "
          "Z.n. ambulant erworbener Pneumonie 2022", BODY),
        P("Anamnese", H2),
        P("Die Patientin stellte sich mit seit etwa einer Woche zunehmender Belastungsdyspnoe (NYHA III), "
          "Orthopnoe sowie beidseitigen Unterschenkelödemen vor. Gewichtszunahme laut Patientin ca. 4 kg. "
          "Kein Thoraxschmerz, keine Synkope. Unter der bisherigen oralen Antikoagulation mit Phenprocoumon "
          "schwankende INR-Werte (zuletzt 1,6 bzw. 3,9).", BODY),
    ])
    footer(c, "Seite 1 von 3")


def p02(c):
    header(c, *KARDIO)
    flow(c, [
        P("Befunde", H2),
        P("<b>Aufnahme:</b> RR 158/92 mmHg, HF 96/min arrhythmisch, SpO2 91 % bei Raumluft, AF 22/min. "
          "Feuchte Rasselgeräusche basal beidseits, Unterschenkelödeme beidseits. Gewicht 58 kg.", BODY),
        P("<b>EKG:</b> Vorhofflimmern mit Kammerfrequenz um 95/min, intermittierend Schrittmacherstimulation, "
          "keine akuten Erregungsrückbildungsstörungen.", BODY),
        P("<b>Echokardiographie (12.10.2026):</b> LVEF 40 %, Mitralinsuffizienz Grad II, kein Perikarderguss "
          "(siehe separater Befund).", BODY),
        P("<b>CT-Thorax nativ (10.10.2026):</b> Pleuraergüsse beidseits, pulmonalvenöse Stauung, kein Infiltrat. "
          "Auf Kontrastmittel wurde bei eingeschränkter Nierenfunktion verzichtet.", BODY),
        P("<b>Labor bei Aufnahme:</b> Kreatinin 1,6 mg/dl, eGFR 32 ml/min/1,73m², Kalium 4,8 mmol/l, "
          "NT-proBNP 2840 pg/ml, HbA1c 7,4 %.", BODY),
        P("Verlauf", H2),
        P("Unter intravenöser Diuretikatherapie kam es zu einer raschen Rekompensation mit Gewichtsreduktion um 3,5 kg. "
          "Bei instabiler INR-Einstellung erfolgte nach Rücksprache mit der Patientin die <b>Umstellung von "
          "Phenprocoumon auf Apixaban</b>. Aufgrund von Körpergewicht unter 60 kg und Kreatinin über 1,5 mg/dl "
          "wählten wir die <b>reduzierte Dosis von 2,5 mg zweimal täglich</b>. Phenprocoumon wurde beendet; "
          "Apixaban wurde nach Abfall der INR unter 2 begonnen.", BODY),
        P("Zur prognostischen Therapie der Herzinsuffizienz wurde <b>Empagliflozin 10 mg</b> neu angesetzt. "
          "Die Torasemid-Dosis wurde auf <b>20 mg täglich erhöht</b>. Ramipril wurde bei grenzwertigem Kalium "
          "in unveränderter niedriger Dosis fortgeführt.", BODY),
        P("<b>Hinweis:</b> Metformin wurde bei einer eGFR unter 30 ml/min wiederholt diskutiert; bei aktuell eGFR 32 "
          "vorerst Fortführung in reduzierter Dosis, Kontrolle der Nierenfunktion dringend empfohlen.", BODY),
        P("Die Patientin hat eine Patientenverfügung; ihre Tochter ist bevollmächtigt.", BODY),
    ])
    footer(c, "Seite 2 von 3")


def p03(c):
    header(c, *KARDIO)
    rows = [["Wirkstoff", "Stärke", "Form", "Mo-Mi-Ab-Na", "Hinweis"],
            ["Apixaban", "2,5 mg", "Tbl.", "1-0-1-0", "NEU, statt Phenprocoumon"],
            ["Bisoprolol", "2,5 mg", "Tbl.", "1-0-0-0", ""],
            ["Ramipril", "2,5 mg", "Tbl.", "1-0-0-0", "Kalium kontrollieren"],
            ["Torasemid", "20 mg", "Tbl.", "1-0-0-0", "Dosis erhöht (vorher 10 mg)"],
            ["Empagliflozin", "10 mg", "Tbl.", "1-0-0-0", "NEU"],
            ["Atorvastatin", "20 mg", "Tbl.", "0-0-1-0", ""],
            ["Metformin", "500 mg", "Tbl.", "1-0-0-0", "reduziert, eGFR beachten"],
            ["Glimepirid", "1 mg", "Tbl.", "1-0-0-0", ""],
            ["Pantoprazol", "20 mg", "Tbl.", "1-0-0-0", ""]]
    flow(c, [
        P("Medikation bei Entlassung", H2),
        table(rows, [38, 22, 16, 28, 66]),
        P("Phenprocoumon (Marcumar) ist <b>abgesetzt</b>. Keine Überlappung mit Apixaban.", BODY),
        P("Empfehlungen", H2),
        P("• Kontrolle von Kreatinin, eGFR und Kalium in 1 Woche beim Hausarzt<br/>"
          "• Tägliche Gewichtskontrolle, bei Zunahme über 2 kg in 3 Tagen Wiedervorstellung<br/>"
          "• Trinkmenge 1,5 l pro Tag<br/>"
          "• Schrittmacher-Kontrolle regulär im 01/2027<br/>"
          "• Re-Evaluation der Metformin-Therapie bei weiterer Verschlechterung der Nierenfunktion", BODY),
        Spacer(1, 6 * mm),
        P("Mit freundlichen kollegialen Grüßen", BODY), Spacer(1, 8 * mm),
        P("Prof. Dr. med. F. Herzog (fiktiv) · Dr. med. J. Puls (fiktiv), Assistenzarzt", BODY),
    ])
    footer(c, "Seite 3 von 3")


def p04(c):
    """GP medication plan, OLD (before the cardiology stay): still Phenprocoumon."""
    c.setFont("Helvetica-Bold", 15)
    c.drawString(20 * mm, H - 20 * mm, "Medikationsplan")
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, H - 26 * mm, f"für: {PATIENT['name']}   geb. am: {PATIENT['birth']}   (FIKTIV)")
    c.drawString(20 * mm, H - 31 * mm, "ausgedruckt von: Dr. med. A. Hausmann, Am Markt 3, 80002 Musterstadt   ·   ausgedruckt am: 02.09.2026")
    c.rect(W - 45 * mm, H - 40 * mm, 25 * mm, 25 * mm)
    c.setFont("Helvetica", 6)
    c.drawCentredString(W - 32.5 * mm, H - 28 * mm, "[2D-Code]")
    rows = [["Wirkstoff", "Handelsname", "Stärke", "Form", "Mo", "Mi", "Ab", "zN", "Einheit", "Grund"],
            ["Phenprocoumon", "Marcumar", "3 mg", "Tabl", "", "", "nach INR", "", "Stück", "Blutverdünnung"],
            ["Bisoprolol", "Bisoprolol", "2,5 mg", "Tabl", "1", "0", "0", "0", "Stück", "Herz"],
            ["Ramipril", "Ramipril", "2,5 mg", "Tabl", "1", "0", "0", "0", "Stück", "Blutdruck"],
            ["Torasemid", "Torem", "10 mg", "Tabl", "1", "0", "0", "0", "Stück", "Wasser"],
            ["Metformin", "Metformin", "1000 mg", "Tabl", "1", "0", "1", "0", "Stück", "Diabetes"],
            ["Glimepirid", "Amaryl", "1 mg", "Tabl", "1", "0", "0", "0", "Stück", "Diabetes"],
            ["Atorvastatin", "Sortis", "20 mg", "Tabl", "0", "0", "1", "0", "Stück", "Cholesterin"],
            ["Pantoprazol", "Pantozol", "20 mg", "Tabl", "1", "0", "0", "0", "Stück", "Magen"]]
    flow(c, [table(rows, [27, 22, 15, 11, 8, 8, 14, 8, 13, 44]), Spacer(1, 4 * mm),
             P("Bitte bringen Sie diesen Plan zu jedem Arzt- und Apothekenbesuch mit.", SMALL)],
         top=H - 46 * mm)
    footer(c, "Seite 1 von 1")


def lab_page(c, date, values, page_label):
    header(c, *LABOR)
    rows = [["Parameter", "Ergebnis", "Einheit", "Referenzbereich", ""]] + values
    flow(c, [
        P("Laborbefund", H1),
        P(f"{PAT_LINE}<br/>Einsender: Hausarztpraxis Dr. med. A. Hausmann · Probeneingang: {date}", BODY),
        Spacer(1, 4 * mm),
        table(rows, [52, 25, 28, 42, 15]),
        Spacer(1, 4 * mm),
        P("H = oberhalb, L = unterhalb des Referenzbereichs. eGFR nach CKD-EPI.", SMALL),
        Spacer(1, 6 * mm),
        P("Technisch und medizinisch freigegeben: Dr. med. M. Probe (fiktiv)", SMALL),
    ])
    footer(c, page_label)


def p05(c):
    lab_page(c, "06.10.2026", [
        ["Natrium", "137", "mmol/l", "136 – 145", ""], ["Kalium", "4,8", "mmol/l", "3,5 – 5,1", ""],
        ["Kreatinin", "1,6", "mg/dl", "0,5 – 0,9", "H"], ["eGFR", "32", "ml/min/1,73m²", "> 60", "L"],
        ["Harnstoff", "68", "mg/dl", "17 – 43", "H"], ["Hämoglobin", "11,9", "g/dl", "12,0 – 15,5", "L"],
        ["Leukozyten", "7,1", "/nl", "3,9 – 10,2", ""], ["CRP", "6", "mg/l", "< 5", "H"],
        ["NT-proBNP", "2840", "pg/ml", "< 450", "H"], ["HbA1c", "7,4", "%", "4,0 – 6,0", "H"],
        ["INR", "1,6", "", "Ziel 2,0 – 3,0", "L"]], "Seite 1 von 1")


def p06(c):
    lab_page(c, "18.11.2026", [
        ["Natrium", "135", "mmol/l", "136 – 145", "L"], ["Kalium", "5,3", "mmol/l", "3,5 – 5,1", "H"],
        ["Kreatinin", "1,9", "mg/dl", "0,5 – 0,9", "H"], ["eGFR", "28", "ml/min/1,73m²", "> 60", "L"],
        ["Harnstoff", "81", "mg/dl", "17 – 43", "H"], ["Hämoglobin", "11,2", "g/dl", "12,0 – 15,5", "L"],
        ["Leukozyten", "6,8", "/nl", "3,9 – 10,2", ""], ["CRP", "4", "mg/l", "< 5", ""],
        ["NT-proBNP", "4120", "pg/ml", "< 450", "H"], ["TSH", "2,1", "mU/l", "0,27 – 4,2", ""]],
        "Seite 1 von 1")


def p07(c):
    header(c, *HAUSARZT)
    flow(c, [
        P("Verordnung von Krankenhausbehandlung (Einweisung)", H1),
        P(f"{PAT_LINE}<br/>{PATIENT['address']} · {PATIENT['insurance']}", BODY), Spacer(1, 4 * mm),
        P("<b>Diagnose / Einweisungsgrund:</b> V.a. erneute kardiale Dekompensation bei bekannter Herzinsuffizienz (I50.13)", BODY),
        P("<b>Fragestellung:</b> Rekompensation, Überprüfung der Diuretika-Dosis, Nierenfunktion?", BODY),
        P("<b>Befund:</b> Seit 4 Tagen zunehmende Luftnot, nachts nur mit erhöhtem Oberkörper, "
          "Ödeme bis Knie, Gewicht +3 kg. SpO2 89 %. Kalium zuletzt 5,3 mmol/l, eGFR 28.", BODY),
        P("<b>Aktuelle Medikation:</b> siehe Medikationsplan und Entlassungsbrief Kardiologie 10/2026.", BODY),
        Spacer(1, 10 * mm),
        P("Musterstadt, 25.11.2026 · Dr. med. A. Hausmann (fiktiv)", BODY),
    ])
    footer(c, "Seite 1 von 1")


def p08(c):
    header(c, *RADIO)
    flow(c, [
        P("Befundbericht: CT Thorax nativ", H1),
        P(f"{PAT_LINE} · Untersuchungsdatum: 10.10.2026", BODY), Spacer(1, 3 * mm),
        P("<b>Klinische Angabe:</b> Dyspnoe, V.a. kardiale Dekompensation, DD Pneumonie.", BODY),
        P("<b>Technik:</b> Native Spiral-CT des Thorax. <b>Auf intravenöses Kontrastmittel wurde bei eingeschränkter "
          "Nierenfunktion (eGFR 32) verzichtet.</b>", BODY),
        P("<b>Befund:</b> Pleuraergüsse beidseits, rechts betont (max. 3,2 cm). Verdickte interlobuläre Septen und "
          "milchglasartige Dichteanhebungen perihilär im Sinne einer pulmonalvenösen Stauung. Kein pneumonisches "
          "Infiltrat abgrenzbar. Kardiomegalie. Schrittmachersonde mit Projektion auf den rechten Ventrikel. "
          "Keine Lungenrundherde.", BODY),
        P("<b>Beurteilung:</b><br/>1. Kardiale Dekompensation mit Pleuraergüssen beidseits und Stauung.<br/>"
          "2. Kein Anhalt für Pneumonie.<br/>3. Schrittmacher in situ.", BODY),
        Spacer(1, 6 * mm), P("Dr. med. R. Strahl (fiktiv), Facharzt für Radiologie", BODY),
    ])
    footer(c, "Seite 1 von 1")


def p09(c):
    header(c, *KARDIO)
    rows = [["Messung", "Wert", "Norm"], ["LVEF (biplan, Simpson)", "40 %", "> 52 %"],
            ["LVEDD", "56 mm", "< 53 mm"], ["Linker Vorhof (Volumen)", "48 ml/m²", "< 34 ml/m²"],
            ["TAPSE", "16 mm", "> 17 mm"], ["sPAP (geschätzt)", "48 mmHg", "< 35 mmHg"]]
    flow(c, [
        P("Transthorakale Echokardiographie", H1),
        P(f"{PAT_LINE} · 12.10.2026 · Rhythmus: Vorhofflimmern", BODY), Spacer(1, 3 * mm),
        table(rows, [70, 40, 40]), Spacer(1, 3 * mm),
        P("<b>Befund:</b> Leicht dilatierter linker Ventrikel mit global leicht- bis mittelgradig eingeschränkter "
          "systolischer Funktion. Mitralklappeninsuffizienz Grad II, Trikuspidalinsuffizienz Grad I. "
          "Schrittmachersonde im rechten Ventrikel. Kein Perikarderguss.", BODY),
        P("<b>Beurteilung:</b> Herzinsuffizienz mit leicht reduzierter Pumpfunktion (HFmrEF), LVEF 40 %. "
          "Pulmonale Hypertonie wahrscheinlich.", BODY),
        Spacer(1, 6 * mm), P("Dr. med. J. Puls (fiktiv)", BODY),
    ])
    footer(c, "Seite 1 von 1")


def p10(c):
    header(c, *ORTHO)
    flow(c, [
        P("Operationsbericht", H1),
        P(f"{PAT_LINE} · OP-Datum: 15.03.2023", BODY), Spacer(1, 3 * mm),
        P("<b>Diagnose:</b> Mediale Schenkelhalsfraktur rechts (Garden IV) nach häuslichem Sturz (S72.01)", BODY),
        P("<b>Operation:</b> Implantation einer zementierten Hüft-Totalendoprothese rechts", BODY),
        P("<b>Implantate:</b> Pfanne Muster-Cup 48 mm, Schaft Muster-Stem Gr. 3 zementiert, Keramikkopf 32 mm "
          "(alle Angaben fiktiv). Implantatpass wurde ausgehändigt.", BODY),
        P("<b>Operateur:</b> Dr. med. K. Knochen (fiktiv) · <b>Anästhesie:</b> Spinalanästhesie", BODY),
        P("<b>Vorgehen:</b> Lagerung in Rückenlage, anterolateraler Zugang. Darstellung der Fraktur, Resektion des "
          "Hüftkopfes. Präparation des Acetabulums, Einbringen der Pfanne in Press-fit-Technik. Markraumpräparation "
          "und zementierte Schaftimplantation. Probereposition, stabile Gelenkführung, Beinlänge seitengleich. "
          "Schichtweiser Wundverschluss, Redon-Drainage.", BODY),
    ])
    footer(c, "Seite 1 von 2")


def p11(c):
    header(c, *ORTHO)
    flow(c, [
        P("<b>Besonderheiten:</b> Bei <b>liegendem Herzschrittmacher (VVI)</b> erfolgte die präoperative Umprogrammierung "
          "in einen starrfrequenten Modus und postoperativ die Rückprogrammierung durch die Kardiologie. "
          "Elektrokauter nur bipolar eingesetzt. Die orale Antikoagulation (damals Phenprocoumon) war präoperativ "
          "pausiert und mit niedermolekularem Heparin überbrückt worden.", BODY),
        P("<b>Postoperativer Verlauf:</b> Komplikationslos. Mobilisation am 1. postoperativen Tag unter Vollbelastung "
          "mit Rollator. Wundverhältnisse reizlos.", BODY),
        P("<b>Procedere:</b> Thromboseprophylaxe bis Wiederaufnahme der oralen Antikoagulation, Fadenzug am 12. Tag, "
          "Röntgenkontrolle nach 6 Wochen.", BODY),
        Spacer(1, 8 * mm), P("Dr. med. K. Knochen (fiktiv)", BODY),
    ])
    footer(c, "Seite 2 von 2")


def p12(c):
    """OLD letter 2022: the ONLY place the penicillin allergy is documented."""
    header(c, *INNERE)
    flow(c, [
        P("Beispielhausen, 22.02.2022", BODY), Spacer(1, 2 * mm),
        P("Arztbrief", H1),
        P(f"{PAT_LINE} · Aufenthalt 14.02.2022 – 22.02.2022", BODY),
        P("Diagnosen", H2),
        P("Ambulant erworbene Pneumonie rechts basal (J18.9) · Permanentes Vorhofflimmern (I48.2) · "
          "Diabetes mellitus Typ 2 (E11.90) · Schrittmacher (VVI) seit 2019", BODY),
        P("Verlauf", H2),
        P("Initiale antibiotische Therapie mit Ampicillin/Sulbactam. Am 2. Tag trat ein generalisiertes, "
          "juckendes makulopapulöses <b>Exanthem</b> auf, das wir als <b>Penicillin-Allergie</b> werteten. "
          "Umstellung auf Clarithromycin, darunter rasche Rückbildung des Exanthems und klinische Besserung. "
          "Die Patientin wurde über die Allergie aufgeklärt; ein Allergiepass wurde empfohlen.", BODY),
        P("<b>CAVE: Penicillin-Allergie (Exanthem, 02/2022).</b>", BODY),
        P("Medikation bei Entlassung", H2),
        P("Phenprocoumon nach INR · Bisoprolol 2,5 mg 1-0-0 · Ramipril 5 mg 1-0-0 · Metformin 1000 mg 1-0-1 · "
          "Sitagliptin 100 mg 1-0-0", BODY),
        Spacer(1, 6 * mm), P("Dr. med. L. Lunge (fiktiv)", BODY),
    ])
    footer(c, "Seite 1 von 1")


def p13(c):
    c.setFont("Helvetica-Bold", 15)
    c.drawString(20 * mm, H - 22 * mm, "Patientenverfügung und Vorsorgevollmacht (Auszug)")
    flow(c, [
        P(f"Ich, <b>{PATIENT['name']}</b>, geb. {PATIENT['birth']}, {PATIENT['address']} (FIKTIV), "
          "bestimme für den Fall, dass ich meinen Willen nicht mehr bilden oder verständlich äußern kann:", BODY),
        Spacer(1, 3 * mm),
        P("[X] Ich wünsche <b>keine Wiederbelebungsmaßnahmen</b> (keine kardiopulmonale Reanimation).", BODY),
        P("[X] Ich wünsche <b>keine Intubation und keine invasive künstliche Beatmung</b>.", BODY),
        P("[ &nbsp;] Ich wünsche keine Dialyse.", BODY),
        P("[X] Ich wünsche eine fachgerechte Schmerz- und Symptombehandlung, auch wenn sie mein Leben verkürzen kann.", BODY),
        P("[X] Nicht-invasive Maßnahmen (z.B. Sauerstoff, Medikamente, Maskenbeatmung) sind ausdrücklich erwünscht.", BODY),
        Spacer(1, 4 * mm),
        P("<b>Vorsorgevollmacht:</b> Ich bevollmächtige meine Tochter <b>Sabine Beispiel</b> (fiktiv), "
          "Tel. 0151 00000000, mich in allen Gesundheitsangelegenheiten zu vertreten.", BODY),
        Spacer(1, 10 * mm),
        P("Musterstadt, 05.06.2024 · Unterschrift: ______________________", BODY),
    ], top=H - 30 * mm)
    footer(c, "Seite 1 von 1")


def p14(c):
    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * mm, H - 20 * mm, "Pflegeüberleitungsbogen")
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, H - 26 * mm, "Ambulanter Pflegedienst Sonnenschein (fiktiv) · 24.11.2026")
    rows = [["Bereich", "Angaben"],
            ["Pflegegrad", "2"],
            ["Mobilität", "Rollator, Sturzgefahr (Sturz 2023 mit Hüftfraktur)"],
            ["Kognition", "orientiert, leicht vergesslich"],
            ["Sinne", "Hörgerät beidseits, Brille"],
            ["Ernährung", "Diabetikerkost, Trinkmenge ca. 1,5 l"],
            ["Ausscheidung", "Harninkontinenz leichtgradig, Vorlagen"],
            ["Haut", "Unterschenkelödeme beidseits, keine Dekubitus"],
            ["Medikamente", "werden vom Pflegedienst wöchentlich gestellt"],
            ["Allergien", "keine bekannt"],
            ["Bezugsperson", "Tochter Sabine Beispiel (fiktiv), Tel. 0151 00000000 – bevollmächtigt"],
            ["Hausärztin", "Dr. med. A. Hausmann (fiktiv), Tel. 089 000000-1"]]
    flow(c, [table(rows, [40, 130])], top=H - 32 * mm)
    footer(c, "Seite 1 von 1")


def p15(c):
    header(c, *DIABETO)
    flow(c, [
        P("Musterstadt, 08.07.2021", BODY), P("Bericht Diabetologie", H1),
        P(f"{PAT_LINE}", BODY),
        P("Befund", H2),
        P("HbA1c 8,1 %, Nüchternglukose 168 mg/dl. Kreatinin 1,1 mg/dl, eGFR 49 ml/min. Keine Hypoglykämien. "
          "Fußstatus unauffällig, Monofilament beidseits erhalten.", BODY),
        P("Therapieempfehlung (Stand 07/2021)", H2),
        P("Metformin 1000 mg 1-0-1 · <b>Sitagliptin 100 mg 1-0-0 neu</b> · Fortführung Ernährungsberatung. "
          "Bei HbA1c über 8 % in 6 Monaten Erwägung eines Basalinsulins.", BODY),
        P("Wiedervorstellung in 6 Monaten.", BODY),
    ])
    footer(c, "Seite 1 von 2")


def p16(c):
    header(c, *DIABETO)
    flow(c, [
        P("Schulungsinhalte und Hinweise", H2),
        P("Die Patientin wurde zu Hypoglykämie-Symptomen, Fußpflege und Ernährung geschult. "
          "Blutzuckerselbstmessung 2x wöchentlich empfohlen. Bei Infekten ggf. Metformin pausieren.", BODY),
        Spacer(1, 6 * mm), P("Dr. med. Z. Zucker (fiktiv)", BODY),
    ])
    footer(c, "Seite 2 von 2")


def p17(c):
    header(c, *HAUSARZT)
    flow(c, [
        P("Diabetes-Verlaufsbogen (DMP)", H1), P(f"{PAT_LINE}", BODY), Spacer(1, 3 * mm),
        table([["Datum", "HbA1c", "eGFR", "Gewicht", "Bemerkung"],
               ["03/2026", "7,1 %", "36", "61 kg", ""],
               ["06/2026", "7,3 %", "34", "62 kg", ""],
               ["10/2026", "7,4 %", "32", "58 kg", "nach Kardiologie"],
               ["11/2026", "–", "28", "61 kg", "Metformin weiter?"]], [25, 22, 22, 25, 76]),
        Spacer(1, 4 * mm),
        P("<b>Notiz:</b> Metformin aktuell 500 mg 1-0-0 laut Kardiologie. Bei eGFR unter 30 Absetzen erwägen.", BODY),
    ])
    footer(c, "Seite 1 von 1")


def p18(c):
    c.setFont("Helvetica-Bold", 16)
    c.drawString(20 * mm, H - 22 * mm, "Muster-Krankenkasse (fiktiv)")
    flow(c, [
        P(f"Frau {PATIENT['name']} · {PATIENT['address']}", BODY), Spacer(1, 6 * mm),
        P("Ihre neue elektronische Gesundheitskarte", H1),
        P("Sehr geehrte Frau Beispiel, anbei erhalten Sie Ihre neue Gesundheitskarte. Bitte vernichten Sie die alte "
          "Karte. Ab dem 01.01.2027 gelten neue Zuzahlungsregeln für Hilfsmittel. Unser Service-Team erreichen Sie "
          "montags bis freitags von 8 bis 18 Uhr. Wussten Sie schon? Mit unserem Bonusprogramm können Sie für "
          "Vorsorgeuntersuchungen Punkte sammeln.", BODY),
        Spacer(1, 6 * mm), P("Mit freundlichen Grüßen<br/>Ihre Muster-Krankenkasse", BODY),
    ], top=H - 30 * mm)
    footer(c, "Seite 1 von 1")


def p19(c):
    """Handwritten fax from the GP: Glimepirid stopped."""
    c.setFont("Courier", 8)
    c.drawString(15 * mm, H - 10 * mm, "20.11.2026 08:14   FAX 089 000000-2   PRAXIS DR. HAUSMANN (FIKTIV)   S. 1/1")
    header(c, *HAUSARZT)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20 * mm, H - 42 * mm, "Telefax / Kurzmitteilung")
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, H - 50 * mm, "An: Pflegedienst Sonnenschein (fiktiv)")
    c.drawString(20 * mm, H - 56 * mm, f"Betreff: {PATIENT['name']}, geb. {PATIENT['birth']} (FIKTIV)")
    y = H - 80 * mm
    for line in ["Glimepirid abgesetzt", "wg. Hypoglykämien (BZ 48 mg/dl)!",
                 "Bitte nicht mehr stellen.", "", "Torasemid ggf. auf 2x 20mg", "nach Rücksprache.",
                 "", "Kalium-Kontrolle Mo.", "                    Hausmann"]:
        handwriting(c, 25 * mm, y, line)
        y -= 11 * mm
    footer(c, "Seite 1 von 1")


PAGES = [p01, p02, p03, p04, p05, p06, p07, p08, p09, p10, p11, p12, p13, p14, p15, p16, p17, p18, p19]
# page 20 = blurry re-photo of page 4 (made in the image step)

DOCUMENTS = [
    {"doc_id": "D01", "type": "discharge_letter", "title": "Entlassungsbrief Kardiologie", "date": "2026-10-14", "pages": [1, 2, 3]},
    {"doc_id": "D02", "type": "medication_plan", "title": "Medikationsplan Hausärztin (veraltet)", "date": "2026-09-02", "pages": [4, 20]},
    {"doc_id": "D03", "type": "lab_report", "title": "Laborbefund", "date": "2026-10-06", "pages": [5]},
    {"doc_id": "D04", "type": "lab_report", "title": "Laborbefund", "date": "2026-11-18", "pages": [6]},
    {"doc_id": "D05", "type": "referral", "title": "Krankenhauseinweisung", "date": "2026-11-25", "pages": [7]},
    {"doc_id": "D06", "type": "imaging_report", "title": "CT Thorax", "date": "2026-10-10", "pages": [8]},
    {"doc_id": "D07", "type": "imaging_report", "title": "Echokardiographie", "date": "2026-10-12", "pages": [9]},
    {"doc_id": "D08", "type": "surgery_report", "title": "OP-Bericht Hüft-TEP rechts", "date": "2023-03-15", "pages": [10, 11]},
    {"doc_id": "D09", "type": "discharge_letter", "title": "Arztbrief Pneumonie", "date": "2022-02-22", "pages": [12]},
    {"doc_id": "D10", "type": "advance_directive", "title": "Patientenverfügung / Vorsorgevollmacht", "date": "2024-06-05", "pages": [13]},
    {"doc_id": "D11", "type": "nursing_transfer", "title": "Pflegeüberleitungsbogen", "date": "2026-11-24", "pages": [14]},
    {"doc_id": "D12", "type": "specialist_letter", "title": "Bericht Diabetologie (veraltet)", "date": "2021-07-08", "pages": [15, 16]},
    {"doc_id": "D13", "type": "other_medical", "title": "Diabetes-Verlaufsbogen", "date": "2026-11", "pages": [17]},
    {"doc_id": "D14", "type": "irrelevant", "title": "Schreiben Krankenkasse", "date": None, "pages": [18]},
    {"doc_id": "D15", "type": "fax_note", "title": "Fax Hausärztin (handschriftlich)", "date": "2026-11-20", "pages": [19]},
]

CURRENT_MEDS = [
    {"name": "Apixaban", "strength": "2,5 mg", "form": "Tbl.", "dosing": "1-0-1-0", "status": "active", "sources": [2, 3], "note": "seit 10/2026 statt Phenprocoumon"},
    {"name": "Bisoprolol", "strength": "2,5 mg", "form": "Tbl.", "dosing": "1-0-0-0", "status": "active", "sources": [3, 4]},
    {"name": "Ramipril", "strength": "2,5 mg", "form": "Tbl.", "dosing": "1-0-0-0", "status": "active", "sources": [3, 4], "note": "Kalium 5,3"},
    {"name": "Torasemid", "strength": "20 mg", "form": "Tbl.", "dosing": "1-0-0-0", "status": "active", "sources": [3], "note": "erhöht von 10 mg; Fax: ggf. 2x 20 mg"},
    {"name": "Empagliflozin", "strength": "10 mg", "form": "Tbl.", "dosing": "1-0-0-0", "status": "new", "sources": [2, 3]},
    {"name": "Atorvastatin", "strength": "20 mg", "form": "Tbl.", "dosing": "0-0-1-0", "status": "active", "sources": [3, 4]},
    {"name": "Metformin", "strength": "500 mg", "form": "Tbl.", "dosing": "1-0-0-0", "status": "active", "sources": [3, 17], "note": "eGFR 28: Kontraindikation prüfen"},
    {"name": "Pantoprazol", "strength": "20 mg", "form": "Tbl.", "dosing": "1-0-0-0", "status": "active", "sources": [3, 4]},
    {"name": "Glimepirid", "strength": "1 mg", "form": "Tbl.", "dosing": "1-0-0-0", "status": "stopped", "sources": [19], "note": "abgesetzt 20.11.2026 wg. Hypoglykämien"},
    {"name": "Phenprocoumon", "strength": "3 mg", "form": "Tbl.", "dosing": "nach INR", "status": "stopped", "sources": [2, 3], "note": "ersetzt durch Apixaban"},
]

CONFLICTS = [
    {"id": "C1", "text": "Medikationsplan (09/2026) nennt Phenprocoumon, Entlassungsbrief (10/2026) Apixaban. Aktuell gilt Apixaban; Doppel-Antikoagulation ausschließen.", "sources": [4, 3]},
    {"id": "C2", "text": "Torasemid 10 mg (Medikationsplan) vs. 20 mg (Entlassungsbrief) vs. ggf. 2x 20 mg (Fax).", "sources": [4, 3, 19]},
    {"id": "C3", "text": "Metformin 1000 mg 1-0-1 (Medikationsplan) vs. 500 mg 1-0-0 (Entlassungsbrief); eGFR inzwischen 28.", "sources": [4, 3, 6]},
    {"id": "C4", "text": "Glimepirid noch im Entlassungsbrief, laut Fax vom 20.11.2026 abgesetzt.", "sources": [3, 19]},
    {"id": "C5", "text": "Pflegeüberleitung: 'Allergien: keine bekannt', Arztbrief 2022: Penicillin-Allergie.", "sources": [14, 12]},
]

NEEDLES = [
    {"id": "N1", "category": "CAVE", "fact": "Orale Antikoagulation: Apixaban 2,5 mg 1-0-1", "sources": [2, 3]},
    {"id": "N2", "category": "CAVE", "fact": "Penicillin-Allergie (Exanthem 2022), nur im alten Arztbrief dokumentiert", "sources": [12]},
    {"id": "N3", "category": "CAVE", "fact": "Herzschrittmacher (VVI) in situ", "sources": [11, 8]},
    {"id": "N4", "category": "CAVE", "fact": "Hüft-TEP rechts (Implantat, 2023)", "sources": [10]},
    {"id": "N5", "category": "CAVE", "fact": "Patientenverfügung: keine Reanimation, keine Intubation/invasive Beatmung; nicht-invasive Maßnahmen erwünscht", "sources": [13]},
    {"id": "N6", "category": "Kontakt", "fact": "Tochter Sabine Beispiel, bevollmächtigt, Tel. 0151 00000000", "sources": [13, 14]},
    {"id": "N7", "category": "Labor", "fact": "eGFR 28 (verschlechtert von 32), CKD G4: Kontrastmittel/Dosierung beachten", "sources": [6, 5]},
    {"id": "N8", "category": "Labor", "fact": "Hyperkaliämie 5,3 mmol/l unter Ramipril", "sources": [6]},
    {"id": "N9", "category": "Medikation", "fact": "Konflikt Phenprocoumon (alt) vs. Apixaban (aktuell)", "sources": [4, 3]},
    {"id": "N10", "category": "Medikation", "fact": "Glimepirid abgesetzt (Hypoglykämie, BZ 48)", "sources": [19]},
    {"id": "N11", "category": "Medikation", "fact": "Metformin trotz eGFR unter 30: prüfen", "sources": [6, 17]},
    {"id": "N12", "category": "Diagnose", "fact": "Herzinsuffizienz HFmrEF, LVEF 40 %, aktuell V.a. erneute Dekompensation", "sources": [9, 7]},
    {"id": "N13", "category": "Medikation", "fact": "Torasemid auf 20 mg erhöht (ggf. 2x 20 mg laut Fax)", "sources": [3, 19]},
]
TRAPS = [
    {"id": "T1", "text": "Sitagliptin (2021/2022) ist NICHT aktuelle Medikation", "sources": [12, 15]},
    {"id": "T2", "text": "Krankenkassenschreiben ist irrelevant und soll ignoriert werden", "sources": [18]},
    {"id": "T3", "text": "Seite 20 ist ein unscharfes Duplikat von Seite 4 (Bitte neu fotografieren / Duplikat)", "sources": [20, 4]},
    {"id": "T4", "text": "Pflegebogen 'Allergien: keine bekannt' ist falsch-negativ", "sources": [14]},
]


# ------------------------------------------------------------ images

def photo_like(gray: np.ndarray, r: np.random.Generator, strong=False) -> np.ndarray:
    """Make a clean scan look like a phone photo: perspective, rotation, shadow, blur, noise, JPEG."""
    h, w = gray.shape
    d = 0.04 * w
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = np.float32([[r.uniform(0, d), r.uniform(0, d)], [w - r.uniform(0, d), r.uniform(0, d)],
                      [w - r.uniform(0, d), h - r.uniform(0, d)], [r.uniform(0, d), h - r.uniform(0, d)]])
    img = cv2.warpPerspective(gray, cv2.getPerspectiveTransform(src, dst), (w, h), borderValue=200)
    m = cv2.getRotationMatrix2D((w / 2, h / 2), r.uniform(-3.5, 3.5), 1.0)
    img = cv2.warpAffine(img, m, (w, h), borderValue=200)
    yy, xx = np.mgrid[0:h, 0:w]
    angle = r.uniform(0, 2 * np.pi)
    shade = 0.78 + 0.22 * (np.cos(angle) * xx / w + np.sin(angle) * yy / h + 1) / 2
    img = img.astype(np.float32) * shade + 18
    img = cv2.GaussianBlur(img, (0, 0), 3.2 if strong else r.uniform(0.6, 1.1))
    img = img + r.normal(0, 4, img.shape)
    img = np.clip(img, 0, 255).astype(np.uint8)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 72])
    return cv2.imdecode(buf, cv2.IMREAD_GRAYSCALE)


def fax_look(gray: np.ndarray) -> np.ndarray:
    small = cv2.resize(gray, None, fx=0.55, fy=0.55, interpolation=cv2.INTER_AREA)
    bw = cv2.threshold(small, 165, 255, cv2.THRESH_BINARY)[1]
    return cv2.resize(bw, (gray.shape[1], gray.shape[0]), interpolation=cv2.INTER_NEAREST)


def main():
    import pypdfium2 as pdfium

    (OUT / "pages_clean").mkdir(parents=True, exist_ok=True)
    (OUT / "pages_photo").mkdir(parents=True, exist_ok=True)
    pdf_path = OUT / "case01_all.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    c.setTitle("case01 – fiktiver Notaufnahme-Fall (FIKTIVE DATEN)")
    for fn in PAGES:
        fn(c)
        c.showPage()
    c.save()

    r = np.random.default_rng(11)
    pdf = pdfium.PdfDocument(str(pdf_path))
    clean_pages = []
    for i in range(len(pdf)):
        pil = pdf[i].render(scale=200 / 72).to_pil().convert("L")
        g = np.array(pil)
        if i == 18:                      # page 19: fax
            g = fax_look(g)
        clean_pages.append(g)
        cv2.imwrite(str(OUT / "pages_clean" / f"case01_p{i + 1:02d}.png"), g)
        cv2.imwrite(str(OUT / "pages_photo" / f"case01_p{i + 1:02d}.jpg"), photo_like(g, r))
    # page 20: blurry re-photo of the medication plan (page 4)
    blurry = photo_like(clean_pages[3], r, strong=True)
    cv2.imwrite(str(OUT / "pages_clean" / "case01_p20.png"), blurry)
    cv2.imwrite(str(OUT / "pages_photo" / "case01_p20.jpg"), blurry)

    answers = {"case_id": "case01", "fictional": True,
               "patient": {k: PATIENT[k] for k in ("name", "birth", "age", "sex")},
               "presentation": "78-jährige Patientin, nächtliche Aufnahme mit Luftnot (V.a. kardiale Dekompensation)",
               "documents": DOCUMENTS, "current_medication": CURRENT_MEDS,
               "conflicts": CONFLICTS, "needles": NEEDLES, "traps": TRAPS}
    (OUT / "case01_answers.json").write_text(json.dumps(answers, ensure_ascii=False, indent=2), encoding="utf-8")

    page_type = {p: d for d in DOCUMENTS for p in d["pages"]}
    src = lambda pages: [{"page": p, "doc_id": page_type[p]["doc_id"]} for p in pages]
    mock = {
        "case_id": "case01", "status": "ready",
        "patient": answers["patient"],
        "pages": [{"page": p, "file": f"case01_p{p:02d}.jpg", "doc_id": page_type[p]["doc_id"],
                   "doc_type": page_type[p]["type"],
                   "status": "retake" if p == 20 else "done",
                   "quality": "too_blurry" if p == 20 else "ok"} for p in range(1, 21)],
        "documents": DOCUMENTS,
        "summary": {
            "cave": [{"text": n["fact"], "sources": src(n["sources"])} for n in NEEDLES if n["category"] == "CAVE"],
            "contacts": [{"text": n["fact"], "sources": src(n["sources"])} for n in NEEDLES if n["category"] == "Kontakt"],
            "diagnoses": [
                {"text": "Herzinsuffizienz HFmrEF, LVEF 40 %", "icd10": "I50.13", "sources": src([1, 9])},
                {"text": "Permanentes Vorhofflimmern", "icd10": "I48.2", "sources": src([1])},
                {"text": "Chronische Niereninsuffizienz G4 (eGFR 28)", "icd10": "N18.4", "sources": src([1, 6])},
                {"text": "Diabetes mellitus Typ 2", "icd10": "E11.90", "sources": src([1])},
                {"text": "Arterielle Hypertonie", "icd10": "I10.90", "sources": src([1])},
                {"text": "Mitralklappeninsuffizienz Grad II", "icd10": "I34.0", "sources": src([1, 9])}],
            "medications": [{**m, "sources": src(m["sources"])} for m in CURRENT_MEDS],
            "conflicts": [{**cf, "sources": src(cf["sources"])} for cf in CONFLICTS],
            "labs": [{"name": "eGFR", "value": "28", "unit": "ml/min/1,73m²", "flag": "L", "trend": "32 → 28", "sources": src([5, 6])},
                     {"name": "Kalium", "value": "5,3", "unit": "mmol/l", "flag": "H", "sources": src([6])},
                     {"name": "NT-proBNP", "value": "4120", "unit": "pg/ml", "flag": "H", "trend": "2840 → 4120", "sources": src([5, 6])}],
            "timeline": [{"date": d["date"], "text": d["title"], "doc_id": d["doc_id"]}
                         for d in sorted(DOCUMENTS, key=lambda d: d["date"] or "") if d["type"] != "irrelevant"],
            "ignored": [{"doc_id": "D14", "reason": "nicht medizinisch relevant"}],
            "text_de": ("78-jährige Patientin mit Luftnot bei V.a. erneute kardiale Dekompensation (HFmrEF, LVEF 40 %). "
                        "CAVE: Apixaban 2,5 mg 1-0-1 [S. 3], Penicillin-Allergie [S. 12], Herzschrittmacher VVI [S. 11], "
                        "Hüft-TEP re. [S. 10], Patientenverfügung: keine Reanimation/Intubation [S. 13]. "
                        "eGFR 28 mit Hyperkaliämie 5,3 [S. 6]. Widersprüche in der Medikation: Phenprocoumon vs. Apixaban [S. 4/3], "
                        "Glimepirid abgesetzt [S. 19], Metformin trotz eGFR unter 30 [S. 17]. "
                        "Ansprechpartnerin: Tochter (bevollmächtigt) [S. 13]."),
        },
        "note": "MOCK DATA for frontend development. Fictional patient.",
    }
    (OUT / "case01_mock_api.json").write_text(json.dumps(mock, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Created 20 pages in {OUT}")
    print("  case01_all.pdf, pages_clean/, pages_photo/, case01_answers.json, case01_mock_api.json")


if __name__ == "__main__":
    main()
