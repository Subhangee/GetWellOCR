from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Settings:
    project_root: Path = Path(__file__).resolve().parent
    input_dir: Path = project_root / "input_docs"
    cleaned_dir: Path = project_root / "cleaned_docs"
    output_dir: Path = project_root / "ocr_output"
    pdf_dpi: int = 300
    ocr_variants: tuple[str, ...] = (
        "original",
        "clahe",
        "clahe_sharpened",
        "background_normalized",
        "adaptive",
    )
    confidence_weight: float = 0.80
    coverage_weight: float = 0.20

SETTINGS = Settings()
