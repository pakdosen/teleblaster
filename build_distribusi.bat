@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

title Build Distribusi - Telegram Blaster By VibeTool.Club

echo ============================================================
echo   Build Distribusi - Telegram Blaster By VibeTool.Club
echo ============================================================
echo.
echo Skrip ini akan:
echo   1. Pastikan venv + dependency terinstall
echo   2. Install PyInstaller (kalau belum)
echo   3. Build aplikasi jadi folder portable
echo   4. Copy hasilnya ke folder "Distribusi\TelegramBlaster"
echo   5. Buat ZIP "Distribusi\TelegramBlaster.zip" siap kirim
echo.

REM ------------------------------------------------------------
REM 1. Pastikan ada Python
REM ------------------------------------------------------------
set "PY="
where py >nul 2>nul && set "PY=py -3"
if "%PY%"=="" where python >nul 2>nul && set "PY=python"
if "%PY%"=="" (
    echo [ERROR] Python tidak ditemukan. Install dari https://www.python.org/downloads/ dulu.
    pause
    exit /b 1
)

REM ------------------------------------------------------------
REM 2. Cek / buat venv di .venv
REM ------------------------------------------------------------
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Membuat virtual environment .venv ...
    %PY% -m venv .venv || (echo [ERROR] Gagal membuat venv & pause & exit /b 1)
)

set "PYEXE=.venv\Scripts\python.exe"
set "PIP=.venv\Scripts\pip.exe"

REM ------------------------------------------------------------
REM 3. Install dependency app + PyInstaller
REM ------------------------------------------------------------
echo [INFO] Update pip ...
"%PYEXE%" -m pip install --upgrade pip >nul

echo [INFO] Install requirements.txt ...
"%PIP%" install -r requirements.txt || (echo [ERROR] Install requirements gagal & pause & exit /b 1)

echo [INFO] Install PyInstaller ...
"%PIP%" install --upgrade pyinstaller || (echo [ERROR] Install PyInstaller gagal & pause & exit /b 1)

REM ------------------------------------------------------------
REM 4. Cek .env wajib ada (akan di-embed ke distribusi)
REM ------------------------------------------------------------
if not exist ".env" (
    echo.
    echo [ERROR] File .env tidak ditemukan di folder ini.
    echo.
    echo   Build dihentikan karena distribusi WAJIB punya .env (berisi API_ID
    echo   dan API_HASH). Tanpa .env, client harus mengisi credential sendiri,
    echo   dan itu bertentangan dengan tujuan distribusi "siap pakai".
    echo.
    echo   CARA FIX:
    echo     1. Buka https://my.telegram.org/apps di browser, login dengan
    echo        nomor Telegram Anda.
    echo     2. Bagian "App configuration" akan menampilkan App api_id (angka)
    echo        dan App api_hash (string panjang).
    echo     3. Buat file ".env" di folder ini, isinya:
    echo            API_ID=12345678
    echo            API_HASH=0123456789abcdef0123456789abcdef
    echo     4. Jalankan ulang build_distribusi.bat
    echo.
    pause
    exit /b 1
)

echo [INFO] .env terdeteksi, akan di-embed ke distribusi.

REM ------------------------------------------------------------
REM 5. Bersihkan build lama
REM ------------------------------------------------------------
echo [INFO] Bersihkan build lama ...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist Distribusi\TelegramBlaster rmdir /s /q Distribusi\TelegramBlaster
if exist Distribusi\TelegramBlaster.zip del /q Distribusi\TelegramBlaster.zip

REM ------------------------------------------------------------
REM 6. Run PyInstaller
REM ------------------------------------------------------------
echo [INFO] Build dengan PyInstaller (bisa 1-3 menit) ...
"%PYEXE%" -m PyInstaller teleblaster.spec --noconfirm || (echo [ERROR] PyInstaller gagal & pause & exit /b 1)

if not exist "dist\TelegramBlaster\TelegramBlaster.exe" (
    echo [ERROR] Output tidak ditemukan di dist\TelegramBlaster\TelegramBlaster.exe
    pause
    exit /b 1
)

REM ------------------------------------------------------------
REM 7. Copy ke folder Distribusi + sertakan README untuk client
REM ------------------------------------------------------------
if not exist Distribusi mkdir Distribusi
echo [INFO] Copy hasil build ke Distribusi\TelegramBlaster ...
xcopy /e /i /q /y "dist\TelegramBlaster" "Distribusi\TelegramBlaster" >nul
copy /y "Distribusi\README-CLIENT.txt" "Distribusi\TelegramBlaster\README.txt" >nul 2>nul

REM ------------------------------------------------------------
REM 8. ZIP folder hasil supaya gampang dikirim
REM ------------------------------------------------------------
echo [INFO] Membuat ZIP Distribusi\TelegramBlaster.zip ...
powershell -NoProfile -Command "Compress-Archive -Path 'Distribusi\TelegramBlaster\*' -DestinationPath 'Distribusi\TelegramBlaster.zip' -Force" || (echo [WARNING] Gagal buat ZIP, folder tetap tersedia.)

echo.
echo ============================================================
echo   BUILD SELESAI
echo ============================================================
echo.
echo Folder portable :  Distribusi\TelegramBlaster\
echo File ZIP siap kirim:  Distribusi\TelegramBlaster.zip
echo.
echo Cara test sebelum kirim ke client:
echo   1. Buka Distribusi\TelegramBlaster
echo   2. Double-click TelegramBlaster.exe
echo   3. Pastikan GUI muncul dan login bisa berjalan
echo.
pause
exit /b 0
