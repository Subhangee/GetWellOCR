"""Turning OCR text lines into structured medications and diagnoses.

v0 = simple rules (regular expressions) for German documents. It is a
baseline: easy to explain, fully offline, and gives a first accuracy number.
Later you can add an LLM-based parser and compare the two in the evaluation.
"""
import re

from .schema import BoundingBox, Diagnosis, ExtractionResult, Medication, OCRLine

# 2,5 mg | 100 mg | 75 µg | 1000 mg | 20 IE
STRENGTH = re.compile(r"(\d+(?:[.,]\d+)?)\s*(mg|µg|ug|mcg|g|ml|IE|I\.E\.)\b", re.IGNORECASE)

# German dosing scheme: 1-0-1-0, 1-0-0, ½-0-½-0, 0,5-0-1 (morning-noon-evening-night)
_DOSE = r"(?:\d+(?:[.,]\d+)?|½|¼|¾)"
DOSING = re.compile(rf"(?<![\d.,]){_DOSE}\s*-\s*{_DOSE}\s*-\s*{_DOSE}(?:\s*-\s*{_DOSE})?(?![\d.,])")

# ICD-10-GM code, e.g. I10.90, E11.9, I48.0 (optional G/V/Z/A certainty letter)
ICD10 = re.compile(r"\b([A-TV-Z]\d{2}(?:\.\d{1,2})?)\s*[GVZA]?\b")
# OCR often reads the letter I as 1, l or |. Inside brackets we can safely fix it:
# "(110.90)" -> "I10.90"
ICD10_OCR_FIX = re.compile(r"\(\s*([1l|])(\d{2}(?:\.\d{1,2})?)\s*\)")

FORMS = re.compile(r"\b(Tbl\.?|Tabl\.?|Kps\.?|Kapseln?|Trpf\.?|Tropfen|Btl\.?|Hub|Amp\.?|Supp\.?)", re.IGNORECASE)
AS_NEEDED = re.compile(r"\b(b\.\s?B\.|bei Bedarf)", re.IGNORECASE)
STATUS_WORDS = {
    "stopped": re.compile(r"\b(abgesetzt|gestoppt|beendet)\b", re.IGNORECASE),
    "paused": re.compile(r"\b(pausiert|pausieren)\b", re.IGNORECASE),
    "new": re.compile(r"\b(neu|neu angesetzt)\b", re.IGNORECASE),
}


def _medication_from_line(line: OCRLine) -> Medication | None:
    text = line.text
    strength = STRENGTH.search(text)
    dosing = DOSING.search(text)
    as_needed = bool(AS_NEEDED.search(text))
    if not (strength or dosing or as_needed):
        return None

    # Name = the words before the strength (or before the dosing scheme)
    cut = strength.start() if strength else (dosing.start() if dosing else len(text))
    name = text[:cut].strip(" -:;,|")
    if not name or not re.search(r"[A-Za-zÄÖÜäöü]{3,}", name):
        return None

    status = "active"
    for label, pattern in STATUS_WORDS.items():
        if pattern.search(text):
            status = label
            break

    form = FORMS.search(text)
    return Medication(
        name=name,
        strength=f"{strength.group(1)} {strength.group(2)}" if strength else None,
        form=form.group(1) if form else None,
        dosing=re.sub(r"\s+", "", dosing.group(0)) if dosing else None,
        as_needed=as_needed,
        status=status,
        source_text=text,
        bbox=line.bbox,
        confidence=line.confidence,
    )


def _diagnosis_from_line(line: OCRLine) -> Diagnosis | None:
    fixed = ICD10_OCR_FIX.sub(lambda m: f"(I{m.group(2)})", line.text)
    m = ICD10.search(fixed)
    if not m:
        return None
    text = (fixed[:m.start()] + fixed[m.end():]).strip(" -:;,()|")
    return Diagnosis(text=text or fixed, icd10=m.group(1), source_text=line.text,
                     bbox=line.bbox, confidence=line.confidence)


def merge_rows(lines: list[OCRLine]) -> list[OCRLine]:
    """Join text pieces that sit on the same row of the page.

    OCR engines often split table columns into separate "lines"
    ("Ramipril 5 mg Tbl." and "1-0-0-0"). If two pieces overlap
    vertically by more than half their height, they belong to one row.
    """
    rows: list[OCRLine] = []
    for line in sorted(lines, key=lambda l: (l.bbox.y0 if l.bbox else 0)):
        if rows and line.bbox and rows[-1].bbox:
            a, b = rows[-1].bbox, line.bbox
            overlap = min(a.y1, b.y1) - max(a.y0, b.y0)
            height = min(a.y1 - a.y0, b.y1 - b.y0)
            if height > 0 and overlap > 0.5 * height:
                left, right = (rows[-1], line) if a.x0 <= b.x0 else (line, rows[-1])
                confs = [c for c in (rows[-1].confidence, line.confidence) if c is not None]
                rows[-1] = OCRLine(
                    text=f"{left.text} {right.text}",
                    bbox=BoundingBox(page=a.page, x0=min(a.x0, b.x0), y0=min(a.y0, b.y0),
                                     x1=max(a.x1, b.x1), y1=max(a.y1, b.y1)),
                    confidence=min(confs) if confs else None,
                )
                continue
        rows.append(line)
    return rows


def parse_lines(lines: list[OCRLine], document_id: str = "doc", engine: str = "unknown") -> ExtractionResult:
    lines = merge_rows(lines)
    result = ExtractionResult(document_id=document_id, engine=engine,
                              raw_text="\n".join(l.text for l in lines))
    for line in lines:
        dx = _diagnosis_from_line(line)
        if dx:
            result.diagnoses.append(dx)
            continue
        med = _medication_from_line(line)
        if med:
            result.medications.append(med)
    if not result.medications:
        result.warnings.append("No medications found. Check image quality or parser rules.")
    return result
