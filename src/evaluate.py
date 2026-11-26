"""Accuracy against the answer files (ground truth).

Medications are matched by fuzzy name similarity (OCR can drop or swap a
letter), then strength and dosing are checked exactly. Diagnoses are matched
by ICD-10 code.

Usage from code:
    from src.evaluate import score_document
    scores = score_document(prediction, truth)
"""
import re

from rapidfuzz import fuzz

from .schema import ExtractionResult

NAME_MATCH_THRESHOLD = 85  # 0-100


def _norm(s: str | None) -> str:
    return re.sub(r"\s+", "", (s or "").lower().replace(",", ".").replace("ug", "µg"))


def _f1(tp: int, n_pred: int, n_true: int) -> dict:
    precision = tp / n_pred if n_pred else 0.0
    recall = tp / n_true if n_true else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def score_document(pred: ExtractionResult, truth: ExtractionResult) -> dict:
    # --- medications ---
    unused = list(pred.medications)
    matched, strength_ok, dosing_ok = 0, 0, 0
    for t in truth.medications:
        best, best_score = None, 0
        for p in unused:
            s = fuzz.token_set_ratio(t.name.lower(), p.name.lower())
            if s > best_score:
                best, best_score = p, s
        if best is not None and best_score >= NAME_MATCH_THRESHOLD:
            matched += 1
            unused.remove(best)
            strength_ok += _norm(best.strength) == _norm(t.strength)
            dosing_ok += _norm(best.dosing) == _norm(t.dosing)

    med = _f1(matched, len(pred.medications), len(truth.medications))

    # --- diagnoses (by ICD code) ---
    true_codes = {_norm(d.icd10) for d in truth.diagnoses if d.icd10}
    pred_codes = {_norm(d.icd10) for d in pred.diagnoses if d.icd10}
    dx = _f1(len(true_codes & pred_codes), len(pred_codes), len(true_codes))

    return {
        "document_id": truth.document_id,
        "med_precision": med["precision"],
        "med_recall": med["recall"],
        "med_f1": med["f1"],
        "strength_accuracy": strength_ok / matched if matched else 0.0,
        "dosing_accuracy": dosing_ok / matched if matched else 0.0,
        "dx_f1": dx["f1"],
    }
