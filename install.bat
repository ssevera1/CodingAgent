@echo off
echo ============================================
echo   CodeAgent Installer
echo   Offline Coding Agent powered by Local LLMs
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

echo [OK] Python found
python --version

:: Check Ollama
ollama --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [WARNING] Ollama is not installed.
    echo Please install Ollama from https://ollama.com
    echo CodeAgent requires Ollama to run local LLMs.
    echo.
    set /p CONTINUE="Continue anyway? (y/N): "
    if /i not "%CONTINUE%"=="y" exit /b 1
) else (
    echo [OK] Ollama found
    ollama --version
)

:: Install CodeAgent
echo.
echo Installing CodeAgent...
pip install -e . 2>nul
if errorlevel 1 (
    echo [WARNING] pip install failed, trying alternative...
    python -m pip install -e .
)

echo.
echo [OK] CodeAgent installed!
echo.

:: Pull the coding model
echo Checking for coding LLM model...
ollama list 2>nul | findstr /i "qwen2.5-coder" >nul 2>&1
if errorlevel 1 (
    echo.
    echo Downloading qwen2.5-coder:7b-instruct model...
    echo This may take a few minutes depending on your connection.
    echo.
    ollama pull qwen2.5-coder:7b-instruct-q4_K_M
) else (
    echo [OK] Coding model already available
)

echo.
echo ============================================
echo   Installation Complete!
echo ============================================
echo.
echo To start CodeAgent:
echo   codeagent
echo.
echo Or with a specific directory:
echo   codeagent --dir C:\your\project
echo.
echo Or with a one-shot prompt:
echo   codeagent "explain this codebase"
echo.
echo For fully offline mode:
echo   codeagent --no-web
echo.
echo Type /help inside CodeAgent for all commands.
echo.
pause
