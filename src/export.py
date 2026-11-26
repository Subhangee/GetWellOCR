"""Exports after the doctor has confirmed the list.

  to_json()          our own format, incl. the correction log (for systems)
  to_fhir()          draft FHIR R4 Bundle (MedicationStatement + Condition)
  to_csv()           medication table (opens in Excel)
  patient_plan_pdf() printable plan for the patient: de, en, tr, zh

The translations below are short fixed phrases, NOT machine translation.
Have a native speaker check them before real use.
"""
import io
import json
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd

from .drugs import purpose

# ---------------------------------------------------------------- texts

LANGUAGES = {"de": "Deutsch", "en": "English", "tr": "Türkçe", "zh": "中文"}

TEXT = {
    "de": {"title": "Mein Medikationsplan", "medicine": "Medikament", "for": "Wofür",
           "times": ["Morgens", "Mittags", "Abends", "Nachts"], "as_needed": "bei Bedarf",
           "stopped": "Abgesetzt: bitte nicht mehr einnehmen",
           "paused": "Pausiert: bitte vorerst nicht einnehmen", "new": "NEU",
           "created": "Erstellt am", "patient": "Patient/in",
           "note": "Die Zahlen bedeuten Anzahl Tabletten. Bei Fragen wenden Sie sich bitte an Ihre Ärztin oder Ihren Arzt.",
           "check": "Ärztlich geprüft: ____________________"},
    "en": {"title": "My medication plan", "medicine": "Medicine", "for": "Used for",
           "times": ["Morning", "Noon", "Evening", "Night"], "as_needed": "as needed",
           "stopped": "Stopped: please do not take any more",
           "paused": "Paused: please do not take for now", "new": "NEW",
           "created": "Created on", "patient": "Patient",
           "note": "Numbers mean number of tablets. If you have questions, please ask your doctor.",
           "check": "Checked by doctor: ____________________"},
    "tr": {"title": "İlaç planım", "medicine": "İlaç", "for": "Ne için",
           "times": ["Sabah", "Öğle", "Akşam", "Gece"], "as_needed": "gerektiğinde",
           "stopped": "Bırakıldı: lütfen artık kullanmayın",
           "paused": "Ara verildi: lütfen şimdilik kullanmayın", "new": "YENİ",
           "created": "Oluşturulma tarihi", "patient": "Hasta",
           "note": "Sayılar tablet sayısını gösterir. Sorularınız için lütfen doktorunuza danışın.",
           "check": "Doktor kontrolü: ____________________"},
    "zh": {"title": "我的用药计划", "medicine": "药品", "for": "用途",
           "times": ["早上", "中午", "晚上", "睡前"], "as_needed": "需要时服用",
           "stopped": "已停用：请不要再服用",
           "paused": "暂停：暂时不要服用", "new": "新药",
           "created": "创建日期", "patient": "患者",
           "note": "数字表示药片数量。如有疑问，请咨询您的医生。",
           "check": "医生核对：____________________"},
}

PURPOSES = {
    "bp":      {"de": "Blutdruck", "en": "Blood pressure", "tr": "Tansiyon", "zh": "血压"},
    "heart":   {"de": "Herz / Blutdruck", "en": "Heart / blood pressure", "tr": "Kalp / tansiyon", "zh": "心脏 / 血压"},
    "water":   {"de": "Entwässerung", "en": "Water tablet", "tr": "İdrar söktürücü", "zh": "利尿"},
    "thin":    {"de": "Blutverdünnung", "en": "Blood thinner", "tr": "Kan sulandırıcı", "zh": "抗凝血"},
    "chol":    {"de": "Cholesterin", "en": "Cholesterol", "tr": "Kolesterol", "zh": "胆固醇"},
    "sugar":   {"de": "Blutzucker", "en": "Blood sugar", "tr": "Kan şekeri", "zh": "血糖"},
    "stomach": {"de": "Magenschutz", "en": "Stomach protection", "tr": "Mide koruma", "zh": "护胃"},
    "thyroid": {"de": "Schilddrüse", "en": "Thyroid", "tr": "Tiroid", "zh": "甲状腺"},
    "pain":    {"de": "Schmerzen / Fieber", "en": "Pain / fever", "tr": "Ağrı / ateş", "zh": "止痛 / 退烧"},
    "gout":    {"de": "Gicht", "en": "Gout", "tr": "Gut", "zh": "痛风"},
}


# ---------------------------------------------------------------- data exports

def to_json(document_id: str, meds: list[dict], dx: list[dict], corrections: list[dict]) -> str:
    payload = {
        "document_id": document_id,
        "confirmed_at": datetime.now().isoformat(timespec="seconds"),
        "medications": meds,
        "diagnoses": dx,
        "corrections": corrections,
        "note": "Fictional demo data. Confirmed by a clinician in the review screen.",
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def to_csv(meds: list[dict]) -> bytes:
    # utf-8-sig so Excel shows umlauts correctly
    return pd.DataFrame(meds).to_csv(index=False, sep=";").encode("utf-8-sig")


FHIR_STATUS = {"active": "active", "new": "active", "stopped": "stopped", "paused": "on-hold"}


def to_fhir(document_id: str, meds: list[dict], dx: list[dict]) -> str:
    """Draft FHIR R4 Bundle. Drugs are text only for now (no PZN/ATC codes yet)."""
    patient_ref = {"reference": "Patient/example", "display": "Fictional patient"}
    entries = []
    for m in meds:
        dosage = " ".join(x for x in [m.get("dosing") or "", "bei Bedarf" if m.get("as_needed") else ""] if x)
        res = {
            "resourceType": "MedicationStatement",
            "id": str(uuid.uuid4()),
            "status": FHIR_STATUS.get(m.get("status") or "active", "unknown"),
            "medicationCodeableConcept": {"text": " ".join(x for x in [m.get("name"), m.get("strength"), m.get("form")] if x)},
            "subject": patient_ref,
            "dosage": [{"text": dosage}] if dosage else [],
        }
        if m.get("status") == "new":
            res["note"] = [{"text": "Newly started (marked 'neu' on source document)"}]
        entries.append({"resource": res})
    for d in dx:
        res = {
            "resourceType": "Condition",
            "id": str(uuid.uuid4()),
            "subject": patient_ref,
            "code": {"text": d.get("text"),
                     "coding": ([{"system": "http://fhir.de/CodeSystem/bfarm/icd-10-gm",
                                  "code": d.get("icd10")}] if d.get("icd10") else [])},
        }
        entries.append({"resource": res})
    bundle = {"resourceType": "Bundle", "type": "collection",
              "identifier": {"value": document_id}, "entry": entries}
    return json.dumps(bundle, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------- patient plan PDF

def _register_fonts(lang: str) -> tuple[str, str]:
    """Return (regular, bold) font names that can show this language's characters."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfbase.ttfonts import TTFont

    if lang == "zh":
        for path in ("C:/Windows/Fonts/simsun.ttc", "C:/Windows/Fonts/msyh.ttc",
                     "C:/Windows/Fonts/simhei.ttf"):
            if Path(path).exists():
                try:
                    pdfmetrics.registerFont(TTFont("ZH", path, subfontIndex=0))
                    return "ZH", "ZH"
                except Exception:
                    pass
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        return "STSong-Light", "STSong-Light"

    pairs = [("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
             ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")]
    for regular, bold in pairs:
        if Path(regular).exists() and Path(bold).exists():
            pdfmetrics.registerFont(TTFont("Plan", regular))
            pdfmetrics.registerFont(TTFont("Plan-Bold", bold))
            return "Plan", "Plan-Bold"
    return "Helvetica", "Helvetica-Bold"   # Turkish letters may not show


def _slots(dosing: str) -> list[str]:
    """'1-0-1-0' -> ['1', '–', '1', '–'];  '1-0-1' -> morning, noon, evening."""
    parts = [p.strip() for p in (dosing or "").split("-")] if dosing else []
    parts = (parts + ["0"] * 4)[:4]
    return ["–" if p in ("0", "") else p for p in parts]


def patient_plan_pdf(meds: list[dict], lang: str = "de", patient: str = "") -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    t = TEXT[lang]
    regular, bold = _register_fonts(lang)
    wrap = "CJK" if lang == "zh" else "LTR"
    p = ParagraphStyle("p", fontName=regular, fontSize=11, leading=15, wordWrap=wrap)
    pb = ParagraphStyle("pb", parent=p, fontName=bold, fontSize=13, leading=17)
    title = ParagraphStyle("t", parent=p, fontName=bold, fontSize=22, leading=28)
    small = ParagraphStyle("s", parent=p, fontSize=9.5, leading=13, textColor=colors.HexColor("#444444"))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=16 * mm, rightMargin=16 * mm,
                            topMargin=14 * mm, bottomMargin=14 * mm, title=t["title"])
    story = [Paragraph(t["title"], title), Spacer(1, 3 * mm)]
    info = f"{t['created']}: {datetime.now().strftime('%d.%m.%Y')}"
    if patient:
        info = f"{t['patient']}: {patient}   ·   " + info
    story += [Paragraph(info, p), Spacer(1, 6 * mm)]

    header = [Paragraph(t["medicine"], pb), Paragraph(t["for"], pb)] + [Paragraph(x, pb) for x in t["times"]]
    rows, style = [header], [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E3EEF0")),
        ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#9AA6B2")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (2, 1), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]
    for m in meds:
        status = m.get("status") or "active"
        name = " ".join(x for x in [m.get("name"), m.get("strength"), m.get("form")] if x)
        if status == "new":
            name += f"  [{t['new']}]"
        cat = purpose(m.get("name") or "")
        use = PURPOSES[cat][lang] if cat else ""
        r = len(rows)
        if status in ("stopped", "paused"):
            rows.append([Paragraph(f"<strike>{name}</strike>", p), Paragraph(use, p),
                         Paragraph(f"<b>{t[status]}</b>" if lang != "zh" else t[status], p), "", "", ""])
            style += [("SPAN", (2, r), (5, r)), ("ALIGN", (2, r), (5, r), "LEFT"),
                      ("BACKGROUND", (0, r), (-1, r), colors.HexColor("#FBE9E7"))]
        elif m.get("as_needed") and not m.get("dosing"):
            rows.append([Paragraph(name, p), Paragraph(use, p), Paragraph(t["as_needed"], p), "", "", ""])
            style += [("SPAN", (2, r), (5, r)), ("ALIGN", (2, r), (5, r), "LEFT")]
        else:
            cells = [Paragraph(f"<font size=14>{s}</font>", p) for s in _slots(m.get("dosing"))]
            rows.append([Paragraph(name, p), Paragraph(use, p)] + cells)
            if status == "new":
                style.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor("#E8F5E9")))

    widths = [85 * mm, 52 * mm] + [32 * mm] * 4
    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle(style))
    story += [table, Spacer(1, 6 * mm), Paragraph(t["note"], small), Spacer(1, 8 * mm),
              Paragraph(t["check"], p)]
    doc.build(story)
    return buf.getvalue()
