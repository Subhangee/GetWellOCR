"""Helpers for the doctor review step: flags, suggestions, and the correction log."""
from . import config
from .drugs import suggest

MED_FIELDS = ["name", "strength", "form", "dosing", "as_needed", "status"]
DX_FIELDS = ["text", "icd10"]


def med_rows(result) -> list[dict]:
    """Medications as editable table rows, with review helpers added."""
    rows = []
    for m in result.medications:
        low = m.confidence is not None and m.confidence < config.LOW_CONFIDENCE
        rows.append({
            "flag": "⚠️ check" if low else "",
            "name": m.name,
            "suggestion": suggest(m.name) or "",
            "use_suggestion": False,
            "strength": m.strength or "",
            "form": m.form or "",
            "dosing": m.dosing or "",
            "as_needed": m.as_needed,
            "status": m.status if m.status != "unknown" else "active",
            "confidence": round(m.confidence, 2) if m.confidence is not None else None,
            "checked": False,
        })
    return rows


def dx_rows(result) -> list[dict]:
    rows = []
    for d in result.diagnoses:
        low = d.confidence is not None and d.confidence < config.LOW_CONFIDENCE
        rows.append({
            "flag": "⚠️ check" if low else "",
            "text": d.text,
            "icd10": d.icd10 or "",
            "confidence": round(d.confidence, 2) if d.confidence is not None else None,
            "checked": False,
        })
    return rows


def finalize_meds(rows: list[dict]) -> list[dict]:
    """Apply accepted spelling suggestions and drop helper columns."""
    out = []
    for r in rows:
        if not str(r.get("name") or "").strip():
            continue
        name = r["suggestion"] if r.get("use_suggestion") and r.get("suggestion") else r["name"]
        out.append({**{f: r.get(f) for f in MED_FIELDS}, "name": name})
    return out


def finalize_dx(rows: list[dict]) -> list[dict]:
    return [{f: r.get(f) for f in DX_FIELDS} for r in rows if str(r.get("text") or "").strip()]


def unchecked_flags(rows: list[dict]) -> int:
    """How many flagged (low-confidence) rows the doctor has not ticked yet."""
    return sum(1 for r in rows if r.get("flag") and not r.get("checked"))


def corrections(original: list[dict], final: list[dict], fields: list[str], key: str) -> list[dict]:
    """Audit log: what the doctor changed compared with what the machine read."""
    log = []
    for i in range(max(len(original), len(final))):
        before = original[i] if i < len(original) else None
        after = final[i] if i < len(final) else None
        if before is None:
            log.append({"row": i + 1, "field": "(row added)", "before": "", "after": str(after.get(key))})
        elif after is None:
            log.append({"row": i + 1, "field": "(row removed)", "before": str(before.get(key)), "after": ""})
        else:
            for f in fields:
                b, a = before.get(f), after.get(f)
                if (b or "") != (a or "") and str(b) != str(a):
                    log.append({"row": i + 1, "field": f, "before": str(b), "after": str(a)})
    return log
