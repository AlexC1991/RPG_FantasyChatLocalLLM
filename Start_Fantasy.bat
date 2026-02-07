@echo off
title VOX-AI Fantasy Chat
color 0A

echo =============================================
echo   VOX-AI FANTASY CHAT - STARTUP
echo =============================================
echo.

REM ========================================
REM 1. CHECK PYTHON INSTALLED
REM ========================================
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo.
    echo Please install Python 3.8+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo [OK] Python found
python --version
echo.

REM ========================================
REM 2. CREATE/ACTIVATE VIRTUAL ENVIRONMENT
REM ========================================
if not exist "venv" (
    echo [INIT] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
    echo.
)

echo [INIT] Activating virtual environment...
call venv\Scripts\activate.bat
echo.

REM ========================================
REM 3. ALWAYS CHECK DEPENDENCIES
REM ========================================
echo [CHECK] Verifying dependencies...

python -c "import flask" 2>nul
if errorlevel 1 (
    echo [INSTALL] Flask not found. Installing dependencies...
    echo This may take a few minutes on first run...
    echo.
    
    python -m pip install --upgrade pip --quiet
    pip install -r requirements.txt
    
    if errorlevel 1 (
        echo.
        echo [ERROR] Dependency installation failed!
        echo.
        echo Try running manually:
        echo   pip install flask psutil llama-cpp-python
        echo.
        pause
        exit /b 1
    )
    
    echo.
    echo [OK] Dependencies installed successfully!
    echo.
) else (
    echo [OK] All dependencies present
    echo.
)

REM ========================================
REM 4. CREATE REQUIRED FOLDERS
REM ========================================
if not exist "models" (
    echo [INIT] Creating models folder...
    mkdir models
)

if not exist "fantasies" (
    echo [INIT] Creating fantasies folder...
    mkdir fantasies
)

if not exist "context_archive" (
    echo [INIT] Creating context_archive folder...
    mkdir context_archive
)

REM ========================================
REM 5. VERIFY ESSENTIAL FILES
REM ========================================
if not exist "templates\index.html" (
    echo [ERROR] templates\index.html not found!
    echo Please ensure the templates folder contains index.html
    echo.
    pause
    exit /b 1
)

if not exist "static\app.js" (
    echo [ERROR] static\app.js not found!
    echo Please ensure the static folder contains app.js and style.css
    echo.
    pause
    exit /b 1
)

if not exist "vox_api.py" (
    echo [ERROR] vox_api.py not found!
    echo Please ensure vox_api.py is in the project root folder
    echo.
    pause
    exit /b 1
)

REM ========================================
REM 6. CHECK FOR MODELS
REM ========================================
dir /b models\*.gguf >nul 2>&1
if errorlevel 1 (
    echo.
    echo [WARNING] No .gguf models found in models folder!
    echo.
    echo You need to download a model file first.
    echo Place .gguf files in the 'models' folder.
    echo.
    echo Recommended models:
    echo   Llama-3.2-3B-Instruct Q5_K_M (4-6GB VRAM)
    echo   Mistral-7B-Instruct Q4_K_M (8GB VRAM)
    echo.
    echo Download from: https://huggingface.co/models?library=gguf
    echo.
    echo The app will still start, but you need a model to chat.
    echo.
    pause
)

REM ========================================
REM 7. START THE APPLICATION
REM ========================================
echo =============================================
echo   STARTING VOX-AI FANTASY CHAT
echo =============================================
echo.
echo [INFO] Server starting at http://127.0.0.1:5000
echo [INFO] Browser will open automatically
echo [INFO] Press Ctrl+C to stop the server
echo.
echo =============================================
echo.

python app.py

REM ========================================
REM 8. CLEANUP ON EXIT
REM ========================================
echo.
echo =============================================
echo   VOX-AI FANTASY CHAT - STOPPED
echo =============================================
echo.

deactivate
pause
