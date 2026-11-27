# GetWellOCR
# getWell_OCR

Local OCR pipeline for difficult scanned medical documents.

## Folder structure

```text
getWell_OCR/
├── input_docs/
├── cleaned_docs/
├── ocr_output/
├── .github/
│   └── copilot-instructions.md
├── scripts/
│   └── setup_windows.ps1
├── config.py
├── preprocess.py
├── ocr_engine.py
├── main.py
├── requirements.txt
└── README.md
```

## Setup in VS Code (Windows)

Recommended: Python 3.11.

Open the `getWell_OCR` folder itself in VS Code.

### Fast setup

In PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup_windows.ps1
```

Then:
1. `Ctrl+Shift+P`
2. `Python: Select Interpreter`
3. choose `.venv`

### Manual setup

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install paddlepaddle==3.2.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
python -m pip install -r requirements.txt
```

## Run

Put PDFs/images into `input_docs/`, then:

```powershell
python main.py
```

The first PaddleOCR run may download model weights. After that, OCR runs locally.

## Main output

For `input_docs/faded_report.pdf`:

```text
ocr_output/
└── faded_report/
    ├── page_001/
    │   ├── original.txt
    │   ├── clahe.txt
    │   ├── clahe_sharpened.txt
    │   ├── background_normalized.txt
    │   ├── adaptive.txt
    │   ├── BEST.txt
    │   └── summary.json
    ├── document_summary.json
    └── full_text.txt
```

`full_text.txt` is the main copyable-text result.

## Why multiple preprocessing variants?

- CLAHE can recover faded local contrast.
- Background normalization helps uneven lighting/shadows.
- Mild sharpening helps slight blur.
- Adaptive thresholding can help dirty/uneven pages.
- Hard binarization can erase faint handwriting.

So the project retains multiple paths and OCRs several versions.

## Privacy and medical safety

- Keep processing local.
- Do not commit real patient files to Git.
- OCR output is not clinically verified data.
- Never silently correct a drug name, dose, frequency, diagnosis, or patient identifier.
- Future normalization should be a suggestion requiring human confirmation.

## Copilot

Project-specific instructions are in:

```text
.github/copilot-instructions.md
```

Useful prompt:

> Read `.github/copilot-instructions.md` and the current codebase. Keep all processing local. First add blur, contrast and skew metrics to each page's summary.json without removing any existing preprocessing paths.

Next prompt:

> Add a modular local TrOCR recognizer for cropped handwritten lines. Do not replace PaddleOCR. Keep both readings and add disagreement flags for human review.
