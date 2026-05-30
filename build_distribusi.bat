@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

title Build Distribusi - Telegram Blaster Free Version

echo ============================================================
echo   Build Distribusi - Telegram Blaster Free Version
echo ============================================================
echo.
echo Skrip ini akan:
echo   1. Pastikan venv + dependency terinstall
echo   2. Install PyInstaller jika belum
echo   3. Build aplikasi jadi 1 file: TelegramBlaster.exe (onefile)
echo   4. Pindahkan hasilnya ke folder "HASIL BUILD\"
echo.

REM ============================================================
REM 1. Pastikan ada Python
REM ============================================================
set "PY="
where py >nul 2>nul && set "PY=py -3"
if "%PY%"=="" where python >nul 2>nul && set "PY=python"
if "%PY%"=="" goto :no_python

REM ============================================================
REM 2. Cek / buat venv di .venv
REM ============================================================
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Membuat virtual environment .venv ...
    %PY% -m venv .venv
    if errorlevel 1 goto :venv_failed
)

set "PYEXE=.venv\Scripts\python.exe"
set "PIP=.venv\Scripts\pip.exe"

REM ============================================================
REM 3. Install dependency app + PyInstaller
REM ============================================================
echo [INFO] Update pip ...
"%PYEXE%" -m pip install --upgrade pip >nul

echo [INFO] Install requirements.txt ...
"%PIP%" install -r requirements.txt
if errorlevel 1 goto :req_failed

echo [INFO] Install PyInstaller ...
"%PIP%" install --upgrade pyinstaller
if errorlevel 1 goto :pyi_install_failed

REM ============================================================
REM 4. Cek .env wajib ada (akan di-embed ke distribusi)
REM ============================================================
if not exist ".env" goto :env_missing
echo [INFO] .env terdeteksi, akan di-embed ke distribusi.

REM ============================================================
REM 5. Bersihkan build lama
REM ============================================================
echo [INFO] Bersihkan build lama ...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "HASIL BUILD" rmdir /s /q "HASIL BUILD"

REM ============================================================
REM 6. Run PyInstaller (mode onefile lewat teleblaster.spec)
REM ============================================================
echo [INFO] Build dengan PyInstaller (bisa 1-3 menit) ...
"%PYEXE%" -m PyInstaller teleblaster.spec --noconfirm
if errorlevel 1 goto :pyi_build_failed

if not exist "dist\TelegramBlaster.exe" goto :no_exe

REM ============================================================
REM 7. Copy ke folder HASIL BUILD
REM ============================================================
if not exist "HASIL BUILD" mkdir "HASIL BUILD"
echo [INFO] Copy TelegramBlaster.exe ke "HASIL BUILD\" ...
copy /y "dist\TelegramBlaster.exe" "HASIL BUILD\TelegramBlaster.exe" >nul
if errorlevel 1 goto :copy_failed

echo.
echo ============================================================
echo   BUILD SELESAI
echo ============================================================
echo.
echo File siap upload ke vibetool.id:
echo   HASIL BUILD\TelegramBlaster.exe
echo.
echo Cara test sebelum kirim ke client:
echo   1. Double-click "HASIL BUILD\TelegramBlaster.exe"
echo   2. Pastikan window login VibeTool muncul
echo   3. Login pakai akun vibetool.id, lalu pastikan GUI utama tampil
echo.
pause
exit /b 0


REM ============================================================
REM Error handlers (terpisah dari blok if untuk hindari bug parser)
REM ============================================================
:no_python
echo.
echo [ERROR] Python tidak ditemukan.
echo Install Python dari https://www.python.org/downloads/ lalu coba lagi.
echo.
pause
exit /b 1

:venv_failed
echo.
echo [ERROR] Gagal membuat virtual environment di .venv
echo.
pause
exit /b 1

:req_failed
echo.
echo [ERROR] Gagal install requirements.txt
echo Pastikan koneksi internet aktif.
echo.
pause
exit /b 1

:pyi_install_failed
echo.
echo [ERROR] Gagal install PyInstaller
echo Pastikan koneksi internet aktif.
echo.
pause
exit /b 1

:env_missing
echo.
echo [ERROR] File .env tidak ditemukan di folder ini.
echo.
echo Build dihentikan karena distribusi WAJIB punya .env yang berisi
echo API_ID dan API_HASH. Tanpa itu, client harus mengisi credential
echo sendiri, dan itu bertentangan dengan tujuan distribusi siap pakai.
echo.
echo CARA FIX:
echo   1. Buka https://my.telegram.org/apps di browser, login dengan
echo      nomor Telegram Anda.
echo   2. Buka bagian App configuration. Catat App api_id berupa angka
echo      dan App api_hash berupa string panjang.
echo   3. Buat file .env di folder ini berisi:
echo          API_ID=12345678
echo          API_HASH=0123456789abcdef0123456789abcdef
echo   4. Jalankan ulang build_distribusi.bat
echo.
pause
exit /b 1

:pyi_build_failed
echo.
echo [ERROR] PyInstaller gagal melakukan build.
echo Lihat log di atas untuk detail error.
echo.
pause
exit /b 1

:no_exe
echo.
echo [ERROR] Output build tidak ditemukan di
echo   dist\TelegramBlaster.exe
echo PyInstaller mungkin gagal silent. Coba ulang skrip.
echo.
pause
exit /b 1

:copy_failed
echo.
echo [ERROR] Gagal copy TelegramBlaster.exe ke folder "HASIL BUILD".
echo Pastikan folder tidak sedang dibuka oleh aplikasi lain.
echo.
pause
exit /b 1
