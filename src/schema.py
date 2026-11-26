"""The data contract.

Every part of the pipeline reads and writes these structures. Agree on them
first, and teammates can work on different parts without breaking each other.
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Where on the page something was found. Coordinates are 0-1 (fraction of page)."""
    page: int = 0
    x0: float
    y0: float
    x1: float
    y1: float


class Medication(BaseModel):
    name: str                                   # e.g. "Ramipril"
    strength: Optional[str] = None              # e.g. "5 mg"
    form: Optional[str] = None                  # e.g. "Tbl."
    dosing: Optional[str] = None                # German scheme, e.g. "1-0-1-0"
    as_needed: bool = False                     # "b.B." (bei Bedarf)
    status: Literal["active", "new", "stopped", "paused", "unknown"] = "unknown"
    source_text: Optional[str] = None           # the raw line it came from
    bbox: Optional[BoundingBox] = None
    confidence: Optional[float] = Field(default=None, ge=0, le=1)


class Diagnosis(BaseModel):
    text: str                                   # e.g. "Essentielle Hypertonie"
    icd10: Optional[str] = None                 # ICD-10-GM, e.g. "I10.90"
    source_text: Optional[str] = None
    bbox: Optional[BoundingBox] = None
    confidence: Optional[float] = Field(default=None, ge=0, le=1)


class OCRLine(BaseModel):
    """One line of text as returned by an OCR engine."""
    text: str
    bbox: Optional[BoundingBox] = None
    confidence: Optional[float] = None


class ExtractionResult(BaseModel):
    document_id: str
    engine: str = "unknown"
    medications: list[Medication] = []
    diagnoses: list[Diagnosis] = []
    raw_text: str = ""
    warnings: list[str] = []
