from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any
import json
from paddleocr import PaddleOCR

@dataclass
class OCRResult:
    text: str
    lines: list[str]
    scores: list[float]
    average_confidence: float
    raw: dict[str, Any]

class LocalPaddleOCR:
    def __init__(self) -> None:
        self.ocr = PaddleOCR(
            lang="en",
            use_doc_orientation_classify=True,
            use_doc_unwarping=False,
            use_textline_orientation=True,
            engine="paddle",
        )

    @staticmethod
    def _to_dict(result):
        value = getattr(result, "json", None)
        if callable(value):
            value = value()
        if isinstance(value, str):
            return json.loads(value)
        if isinstance(value, dict):
            return value
        return {"repr": repr(result)}

    @staticmethod
    def _extract(raw):
        data = raw.get("res", raw)
        texts = data.get("rec_texts") or data.get("texts") or []
        scores = data.get("rec_scores") or data.get("scores") or []
        texts = [str(x) for x in texts]
        clean_scores = []
        for s in scores:
            try:
                clean_scores.append(float(s))
            except Exception:
                clean_scores.append(0.0)
        if len(clean_scores) < len(texts):
            clean_scores.extend([0.0] * (len(texts) - len(clean_scores)))
        return texts, clean_scores

    def recognize(self, image_path: Path) -> OCRResult:
        preds = list(self.ocr.predict(str(image_path)))
        lines, scores, raws = [], [], []
        for pred in preds:
            raw = self._to_dict(pred)
            raws.append(raw)
            t, s = self._extract(raw)
            lines.extend(t)
            scores.extend(s)
        return OCRResult(
            text="\n".join(lines),
            lines=lines,
            scores=scores,
            average_confidence=mean(scores) if scores else 0.0,
            raw={"results": raws},
        )
