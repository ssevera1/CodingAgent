@echo off
title CodeAgent - Offline Coding Agent
cd /d "%~dp0"

:: Check if Ollama is running, start it if not
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I "ollama.exe" >NUL
if errorlevel 1 (
    echo Starting Ollama...
    start /min "" ollama serve
    timeout /t 3 /nobreak >NUL
)

:: Check if installed
pip show codeagent >NUL 2>&1
if errorlevel 1 (
    echo First run - installing CodeAgent...
    pip install -e . >NUL 2>&1
)

:: Launch
codeagent
pause
