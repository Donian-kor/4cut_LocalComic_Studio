@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo [4Cut Local] Python virtual environment not found.
    echo Creating .venv...
    python -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment. Install Python 3.10+ first.
        pause
        exit /b 1
    )
    echo Installing dependencies...
    .venv\Scripts\python.exe -m pip install --upgrade pip
    .venv\Scripts\python.exe -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Dependency installation failed.
        pause
        exit /b 1
    )
)
.venv\Scripts\python.exe app.py
if errorlevel 1 pause
endlocal
