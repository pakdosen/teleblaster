#!/usr/bin/env bash
# Linux smoke-test build (untuk verifikasi spec PyInstaller).
# Untuk build distribusi Windows yang dikirim ke client, jalankan
# build_distribusi.bat di mesin Windows.

set -euo pipefail
cd "$(dirname "$0")"

echo "[INFO] Build Distribusi (Linux smoke test, onefile) ..."

if [[ ! -d ".venv" ]]; then
    python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
pip install --quiet --upgrade pyinstaller

rm -rf build dist "HASIL BUILD"

pyinstaller teleblaster.spec --noconfirm

if [[ ! -f "dist/TelegramBlaster" ]]; then
    echo "[ERROR] Output tidak ditemukan." >&2
    exit 1
fi

mkdir -p "HASIL BUILD"
cp -f "dist/TelegramBlaster" "HASIL BUILD/TelegramBlaster"

echo "[OK] File portable (Linux ELF, hanya untuk smoke test):"
echo "     HASIL BUILD/TelegramBlaster"
echo
echo "Untuk build distribusi Windows (.exe), jalankan build_distribusi.bat"
echo "di mesin Windows."
