# TelegramScraper Rebuild

Rebuild implementasi berbasis README publik TelegramScraper.

## Status

Versi saat ini: `v0.1` (fitur inti sudah ada, beberapa alur advanced masih bertahap).

## Fitur v0.1

- Multi-session storage terenkripsi (Fernet + PBKDF2)
- Login akun via phone OTP (+ 2FA)
- Login via QR code (scan dari Telegram mobile)
- Import TData best-effort via session string converter eksternal
- Scrape members dari member list (visible)
- Scrape hidden participants dari message history + checkpoint
- Add members mode rush/calm
- Broadcast pesan dari markdown sederhana
- Session management (list/test/remove inactive)
- Cooldown persistence untuk FloodWait
- Atomic writes untuk JSON/CSV

## Setup

1. Install dependencies

```bash
pip install -r requirements.txt
```

2. Buat file `.env`

```env
API_ID=123456
API_HASH=your_api_hash
```

3. Jalankan

```bash
python main.py
```

## Run Desktop GUI

Untuk mode desktop yang lebih user-friendly:

```bash
python gui_app.py
```

GUI menyediakan tab untuk Login, Scraper, Adder, Broadcast, dan Sessions.

Di tab `Members Scraper`, gunakan tombol `Load My Joined Groups` setelah mengisi encryption password.
Daftar grup yang sudah diikuti akun login akan tampil, lalu klik `Use Selected Group` agar target scrape terisi otomatis.

Hasil scrape otomatis tersedia di tab `Broadcast` dalam bentuk daftar member yang bisa dipilih (multi-select).
Aktifkan opsi `Broadcast only selected members` untuk kirim hanya ke member yang dipilih.

Tab `Broadcast` juga mendukung compose langsung tanpa edit file:
- Input text pesan langsung di GUI
- Input link (satu link per baris)
- Lampiran file campuran (gambar, video, dokumen/teks)
- Kombinasi text + link + attachment dalam satu kali broadcast
- Setting delay acak min/max antar pengiriman (contoh 5 sampai 20 detik)

## One-Click Run (No Terminal)

Untuk user non-teknis, cukup double-click file berikut di folder project:

- `Run-GUI.vbs` (recommended, tanpa jendela terminal)
- `Run-GUI.bat` (fallback launcher)

Launcher akan mencoba `pythonw.exe` dari virtual environment otomatis.

## Quick QR Test

Untuk uji cepat QR login end-to-end (tanpa menyimpan session), jalankan:

```bash
python quick_qr_test.py
```

Jika berhasil, script akan menampilkan info akun (`user id`, `phone`, `username`).

## Catatan

- Gunakan tool ini hanya pada akun dan grup yang Anda miliki izin untuk mengelola.
- Import TData langsung tanpa converter belum tersedia karena kompatibilitas format Telegram Desktop yang berubah antar versi.
