# One-time project setup for Windows (run in the VS Code terminal, PowerShell)
#   .\setup_windows.ps1
# If PowerShell refuses to run scripts, run this once first:
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

Write-Host "1/4 Creating virtual environment (.venv)..."
py -3.12 -m venv .venv

Write-Host "2/4 Activating it..."
. .\.venv\Scripts\Activate.ps1

Write-Host "3/4 Installing packages (takes a few minutes)..."
python -m pip install --upgrade pip
pip install -r requirements.txt

Write-Host "4/4 Creating your .env file from the template..."
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }

Write-Host ""
Write-Host "Done. Next: open .env and paste your Azure key, then run:"
Write-Host "  python scripts\check_setup.py"
