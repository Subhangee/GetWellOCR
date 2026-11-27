r"""Download the PaddleOCR PP-OCRv6 models once (about 135 MB). After that, OCR runs offline.

Run from the project folder:   python scripts\download_paddle_models.py
Models go to models\ (in .gitignore, never committed).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from huggingface_hub import snapshot_download

from src import config
from src.extract import PADDLE_MODELS, paddle_models_missing

for name in PADDLE_MODELS:
    target = config.PADDLE_MODEL_DIR / name
    print(f"Downloading {name} -> {target}")
    snapshot_download(repo_id=f"PaddlePaddle/{name}", local_dir=target)

missing = paddle_models_missing()
print("Done. Use it with:  python scripts\\process_case.py --engine paddle" if not missing
      else f"Still missing: {', '.join(missing)}")
