# GetWellOCR

Local OCR pipeline for difficult scanned medical documents: faded reports, blurred scans, printed medical text and handwritten prescriptions.

Everything runs on your own machine. No cloud OCR, no uploads.

It uses two simple scripts:

1. `preprocess.py` cleans each page in several ways (contrast, sharpening, background removal).
2. `ocr.py` reads the cleaned images with PaddleOCR (PP-OCRv6 models) and keeps the most confident result per page.

## Folder structure

```text
GetWellOCR/
├── input_docs/          # put your PDFs / images here (not committed)
├── cleaned_docs/        # preprocessed page images (not committed)
├── ocr_output/          # OCR text results (not committed)
├── models/              # PP-OCRv6 model files (downloaded, not committed)
│   ├── PP-OCRv6_medium_det/
│   └── PP-OCRv6_medium_rec/
├── scripts/
│   └── setup_windows.ps1
├── .github/
│   └── copilot-instructions.md
├── preprocess.py
├── ocr.py
├── requirements.txt
└── README.md
```

## Setup (Windows, VS Code)

Recommended: Python 3.11.

### 1. Get the code

```powershell
git clone https://github.com/Subhangee/GetWellOCR.git
cd GetWellOCR
```

Open the `GetWellOCR` folder in VS Code (File → Open Folder).

### 2. Create the environment and install packages

In the VS Code terminal (PowerShell):

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install paddlepaddle -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
python -m pip install -r requirements.txt
```

`requirements.txt` needs `paddleocr>=3.7,<3.8`. PP-OCRv6 only exists from PaddleOCR 3.7 on.

Then select the interpreter: `Ctrl+Shift+P` → `Python: Select Interpreter` → `.venv`.

### 3. Download the models

The model files are not stored in Git (they are 60–75 MB each). Download them once:

```powershell
python -m pip install -U huggingface_hub
hf download PaddlePaddle/PP-OCRv6_medium_det --local-dir models\PP-OCRv6_medium_det
hf download PaddlePaddle/PP-OCRv6_medium_rec --local-dir models\PP-OCRv6_medium_rec
```

If `hf` is not recognised, use `huggingface-cli download` with the same arguments.

Each folder should then contain `inference.json`, `inference.pdiparams` and `inference.yml`.

## Run

Put PDFs or images (`.pdf`, `.png`, `.jpg`, `.jpeg`, `.tif`, `.tiff`) into `input_docs/`, then:

```powershell
python preprocess.py
python ocr.py
```

Run both from the project folder, since the scripts use relative paths.

## Output

For `input_docs/faded_report.pdf`:

```text
cleaned_docs/
└── faded_report/
    └── page_1/
        ├── original.png
        ├── gray.png
        ├── clahe.png
        ├── sharpened.png
        ├── normalized.png
        └── adaptive.png

ocr_output/
└── faded_report/
    └── page_1/
        ├── clahe.txt
        ├── sharpened.txt
        ├── normalized.txt
        └── BEST.txt
```

`BEST.txt` is the result with the highest average OCR confidence for that page. The other `.txt` files are kept so you can compare readings.

## Why several preprocessing variants?

- **CLAHE** recovers faded local contrast.
- **Sharpening** helps with slight blur.
- **Background normalization** helps with uneven lighting and shadows.
- **Adaptive thresholding** can help with dirty or uneven pages, but hard binarization can erase faint handwriting.

No single cleanup works for every scan, so the pipeline OCRs several versions and keeps all of them.

## Troubleshooting

**`NotImplementedError: ConvertPirAttribute2RuntimeAttribute not support ...`**
This is a known bug in PaddlePaddle 3.3.0's CPU acceleration (oneDNN). `ocr.py` avoids it by passing `enable_mkldnn=False` to `PaddleOCR(...)`. OCR runs slightly slower, but works.

**OCR tries to download models / fails offline**
Check that the `models/` folders contain the three `inference.*` files (see step 3).

## Privacy and medical safety

- Keep processing local.
- Never commit real patient files. `input_docs/`, `cleaned_docs/` and `ocr_output/` are excluded in `.gitignore`.
- OCR output is not clinically verified data.
- Never silently correct a drug name, dose, frequency, diagnosis or patient identifier.
- Any future normalization should be a suggestion that a human confirms.

## Roadmap

1. Add blur, contrast and skew quality metrics per page.
2. Benchmark the preprocessing variants.
3. Add a local TrOCR recognizer for cropped handwritten lines, alongside PaddleOCR.
4. Flag disagreements between PaddleOCR and TrOCR for human review.
5. Extract medications and diagnoses with source provenance.

Project instructions for GitHub Copilot are in `.github/copilot-instructions.md`.
