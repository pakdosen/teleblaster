@echo off
setlocal
cd /d "%~dp0"

if exist "%~dp0\.venv\Scripts\pythonw.exe" (
  "%~dp0\.venv\Scripts\pythonw.exe" "%~dp0\gui_app.py"
  exit /b
)

if exist "%~dp0\..\.venv\Scripts\pythonw.exe" (
  "%~dp0\..\.venv\Scripts\pythonw.exe" "%~dp0\gui_app.py"
  exit /b
)

start "TelegramScraper GUI" /B pythonw "%~dp0\gui_app.py"
