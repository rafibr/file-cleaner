# File Organizer AI

File Organizer AI adalah aplikasi desktop berbasis Python yang membantu Anda menganalisis isi dokumen, mengelompokkannya secara otomatis dengan bantuan Google Gemini, dan merapikan struktur folder dengan sekali klik.

## Fitur Utama

- Pilih folder sumber dan lihat daftar file yang ditemukan.
- Analisis isi dokumen (TXT, PDF, DOCX, dan beberapa tipe teks lainnya).
- Panggilan ke Google Gemini (`gemini-2.5-flash`) untuk mengelompokkan file berdasarkan kesamaan konteks.
- Deteksi file duplikat menggunakan hash SHA-256.
- Preview hasil pengelompokan sebelum memindahkan file.
- Undo untuk membatalkan pemindahan terakhir.
- Penulisan `metadata.txt` untuk setiap grup serta ekspor `metadata_summary.csv`.
- GUI ramah pengguna menggunakan `customtkinter` dengan fallback ke `tkinter` standar.

## Persyaratan

- Python 3.10 atau lebih baru.
- API key Google Gemini dengan akses ke model `gemini-2.5-flash`.
- Dependensi yang terdaftar pada `requirements.txt`.

## Konfigurasi

Salin `config.yaml` dan isi dengan kredensial Anda:

```yaml
gemini_api_key: "YOUR_API_KEY_HERE"
model: "gemini-2.5-flash"
similarity_threshold: 0.85
output_folder: "organized_files"
```

## Cara Menjalankan

1. Buat dan aktifkan lingkungan virtual (opsional namun direkomendasikan).
2. Instal dependensi:

   ```bash
   pip install -r requirements.txt
   ```

3. Jalankan aplikasi:

   ```bash
   python main.py
   ```

## Catatan

- Aplikasi akan mencoba menggunakan `customtkinter`. Jika tidak tersedia, aplikasi otomatis kembali menggunakan widget `tkinter` standar.
- Pemanggilan API Gemini membutuhkan koneksi internet dan kuota penggunaan.
- Saat memindahkan file, aplikasi menyimpan daftar operasi untuk mendukung fitur Undo.
- Jika API gagal merespons, aplikasi menyediakan fallback pengelompokan berbasis tipe file sehingga proses tetap berjalan.

## Lisensi

Proyek ini dirilis untuk tujuan demonstrasi. Silakan modifikasi sesuai kebutuhan.
