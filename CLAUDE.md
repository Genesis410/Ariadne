# ARIADNE — Project Rules & Guidelines

Ariadne adalah verifikator otomatis dunia prosedural untuk game developer indie.
Alat ini menguji ribuan seed secara paralel via IPC black-box JSON Lines.
Ariadne memangkas peta rusak menjadi Minimal Failing Map (subgrid bounding box) untuk issue tracking.
Mendukung regression testing instan melalui Seed Vault di CI/CD.

## Wajib Dibaca di Awal Sesi
Sebelum mulai kerja, baca file berikut:
- `.confiential/00-context/CONTEXT_CACHE.md` — Status aktif, keputusan kunci, area rapuh
- `.confiential/00-context/KNOWLEDGE_GRAPH.md` — Relasi antar modul dan arsitektur sistem
- `.confiential/00-context/GLOSSARY.md` — Definisi resmi terminologi domain
- `.confiential/04-execution/TASKS.md` — Daftar tugas aktif dan dependensi
- `.confiential/04-execution/PROGRESS.md` — Log perkembangan sesi terakhir

## Command Proyek
- Install dependensi: `pip install -e .[dev]`
- Jalankan CLI lokal: `ariadne --help`
- Jalankan test suite: `pytest`
- Jalankan lint & typecheck: `ruff check . && mypy ariadne`
- Build single binary executable (.exe): `pyinstaller ariadne.spec`

## Konvensi Kode
- **Bahasa**: Python 3.12+ untuk core CLI, GDScript untuk template adapter Godot.
- **Naming**: `snake_case` untuk fungsi dan variabel Python, `PascalCase` untuk class, `UPPER_SNAKE` untuk konstanta.
- **Struktur File**: Modul diletakkan di `src/ariadne/` dibagi per tanggung jawab (cli, runner, checker, shrinker, vault, license).
- **Error Handling**: Wajib gunakan taksonomi error eksplisit (`timeout`, `crash`, `invalid_json`, `property_violation`). Jangan pernah menelan exception secara diam-diam.
- **Komentar & Dokumen**: Bahasa Indonesia atau Inggris teknis ringkas, prioritaskan "mengapa" daripada "apa".

## Boundaries (Batasan)
- **Selalu Dilakukan**:
  - Validasi schema versi (`schema_version = 1`) pada konfigurasi `ariadne.toml`.
  - Pasang timeout dan watchdog di setiap eksekusi generator eksternal.
  - Tulis minimal 1 test kasus nyata untuk setiap fitur baru sebelum menyatakan selesai.
- **Harus Tanya Dulu**:
  - Mengubah skema protokol IPC JSON Lines (`ARIADNE:{...}`).
  - Menambah dependensi pihak ketiga baru ke `pyproject.toml`.
  - Mengubah format file regresi `.ariadne/vault.jsonl`.
- **Dilarang**:
  - Manipulasi choice sequence PRNG (shrinking wajib Bounding-Box Pruning pada grid output).
  - Mengirim network telemetry atau cek lisensi online (Ariadne 100% offline).
  - Menghapus baris/kolom tengah pada grid peta saat shrinking (merusak topologi).

## Aturan Workflow
1. Satu task fokus per sesi, selesaikan sampai tuntas.
2. Wajib uji manual atau `pytest` sebelum menutup task.
3. Update `.confiential/04-execution/PROGRESS.md` dan `TASKS.md` di akhir setiap sesi.
