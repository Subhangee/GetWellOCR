$ErrorActionPreference = "Stop"

py -3.11 -m venv .venv
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install paddlepaddle==3.2.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
python -m pip install -r requirements.txt
python -c "import paddle, cv2, pymupdf; from paddleocr import PaddleOCR; print('Paddle:', paddle.__version__); print('Setup OK')"

Write-Host "Done. Select .venv as the VS Code Python interpreter."
