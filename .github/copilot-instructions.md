# getWell_OCR — GitHub Copilot Instructions

## Goal
Build a fully local, privacy-preserving OCR pipeline for difficult scanned medical documents:
- faded reports
- blurred scans
- printed medical text
- handwritten prescriptions

The goal is to recover as much copyable text as possible while preserving uncertainty.

## Fixed folder structure
- `input_docs/` — source PDFs/images
- `cleaned_docs/` — preprocessing variants
- `ocr_output/` — OCR text/JSON/confidence summaries
- `.github/`
- `scripts/`

## Current architecture
1. Read PDF/image locally.
2. Render PDFs at 300 DPI.
3. Produce: original, gray, denoised, CLAHE, CLAHE+sharpening, background-normalized, Otsu, adaptive threshold.
4. OCR several variants with local PaddleOCR.
5. Keep every OCR result.
6. Select a provisional best result using confidence + text-coverage.
7. Save all intermediate images, OCR readings, raw JSON, summaries, and `full_text.txt`.

## Critical constraints
- Everything must run locally in VS Code on Windows.
- Do not add cloud OCR APIs or remote LLM APIs.
- Do not upload patient data anywhere.
- Never silently correct medications, diagnoses, dosages, frequencies, or patient identifiers.
- Preserve raw OCR separately from any future normalization/suggestion layer.
- Flag low-confidence/conflicting medical values for human review.
- Keep the code modular enough to add TrOCR later.
- Avoid destructive preprocessing as the only path because faint handwriting may disappear.
- Use `pathlib.Path`.
- Use `pymupdf`, not the unrelated PyPI package `fitz`.

## Near-term roadmap
1. Add blur/contrast/skew quality metrics.
2. Benchmark preprocessing variants.
3. Add local TrOCR for cropped handwritten lines.
4. Compare PaddleOCR vs TrOCR and flag disagreement.
5. Add medications/diagnoses extraction with source provenance.
6. Add human-review UI.
7. Add structured JSON / later FHIR export.

## Definition of done for the current MVP
Running `python main.py` with files in `input_docs/` should:
- create preprocessing variants in `cleaned_docs/`
- run local OCR
- compare OCR candidates
- write copyable text to `ocr_output/<document>/full_text.txt`
- preserve detailed per-page outputs
