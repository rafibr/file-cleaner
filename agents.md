

### 🎯 **PROMPT UNTUK CHATGPT CODEX**

> **Tujuan Utama:**
> Buat aplikasi desktop berbasis Python dengan GUI yang dapat:
>
> 1. Memilih folder dari file explorer.
> 2. Menganalisis isi file di dalam folder (nama, isi teks, metadata, dll).
> 3. Mengelompokkan file berdasarkan **kemiripan konteks atau topik** (dengan AI dari **Google Gemini model `gemini-2.5-flash`**).
> 4. Memberi tanda untuk file yang kemungkinan **duplikat**.
> 5. Membuat **file metadata `.txt`** di setiap folder hasil pengelompokan berisi ringkasan isi dan daftar file di dalamnya.
> 6. Menyediakan antarmuka **GUI sederhana (misalnya dengan `tkinter` atau `customtkinter`)** untuk pengguna non-teknis.
> 7. Menyertakan file konfigurasi `config.yaml` untuk menyimpan API key Gemini dan pengaturan dasar.

---

### 💡 **Spesifikasi Detail Aplikasi**

#### 1. Struktur Folder Proyek

```
file_organizer_ai/
│
├── main.py
├── ai_engine.py
├── file_utils.py
├── gui.py
├── config.yaml          ← untuk API key dan model Gemini
├── requirements.txt
└── README.md
```

#### 2. Fitur Utama

* **GUI utama:**

  * Tombol “Pilih Folder”
  * Tampilan daftar file yang ditemukan
  * Tombol “Analisis & Kelompokkan”
  * Progress bar selama proses
  * Tombol “Buka Folder Hasil”
  * Log aktivitas (misalnya hasil grouping, duplikat terdeteksi)

* **Fungsi AI (di `ai_engine.py`):**

  * Mengirim prompt ke Gemini 2.5 Flash API (melalui REST API call)
  * Menganalisis konten file (teks, nama, metadata)
  * Mengembalikan hasil klasifikasi / pengelompokan (misalnya kategori dokumen, topik, atau proyek)
  * Mendeteksi file serupa (kemiripan di atas threshold tertentu, misalnya 85%)

* **Fungsi File Handling (di `file_utils.py`):**

  * Membaca isi file (txt, docx, pdf — hanya teks)
  * Menghitung hash file untuk mendeteksi duplikat
  * Membuat folder baru berdasarkan hasil grouping
  * Menulis file metadata.txt di setiap folder hasil

* **File `config.yaml`:**

  ```yaml
  gemini_api_key: "YOUR_API_KEY_HERE"
  model: "gemini-2.5-flash"
  similarity_threshold: 0.85
  output_folder: "organized_files"
  ```

* **Output Contoh Folder Setelah Dirapikan:**

  ```
  organized_files/
  ├── Laporan_Kegiatan/
  │   ├── laporan1.docx
  │   ├── laporan2.pdf
  │   └── metadata.txt
  ├── Surat_Resmi/
  │   ├── surat_kadis.docx
  │   └── metadata.txt
  └── Duplikat/
      ├── laporan1 (copy).docx
      └── metadata.txt
  ```

#### 3. Contoh Logika Pengelompokan (AI Prompt ke Gemini)

```python
prompt = f"""
Anda adalah asisten AI yang membantu mengelompokkan file berdasarkan kesamaan konteks isi dokumen.
Berikut daftar file dengan ringkasan isi:
{summary_of_files}

Kelompokkan file berdasarkan topik atau tujuan penggunaan (misalnya laporan, surat resmi, dokumen kontrak, data teknis, dll).
Berikan hasil dalam format JSON seperti contoh:
[
  {"group_name": "Laporan Kegiatan", "files": ["laporan1.docx", "laporan2.pdf"]},
  {"group_name": "Surat Resmi", "files": ["surat_kadis.docx"]}
]
"""
```

#### 4. Teknologi yang Dipakai

* **Python 3.10+**
* Library:

  * `tkinter` atau `customtkinter` (GUI)
  * `requests` (API Gemini)
  * `PyYAML` (config)
  * `tqdm` (progress bar)
  * `pandas` (opsional untuk analisis file)
  * `python-docx`, `PyPDF2` (baca isi dokumen)
  * `hashlib`, `os`, `shutil` (manajemen file)

#### 5. Alur Proses Program

1. User buka aplikasi GUI.
2. Klik **“Pilih Folder”** → pilih direktori target.
3. Program menampilkan daftar file yang ditemukan.
4. Klik **“Analisis & Kelompokkan”** →

   * Aplikasi baca isi file dan buat ringkasan singkat per file.
   * Kirim data ke Gemini API.
   * Terima hasil grouping dalam JSON.
5. Program membuat folder hasil grouping dan memindahkan file sesuai kategorinya.
6. Buat file `metadata.txt` di setiap folder berisi:

   * Nama folder
   * Daftar file
   * Ringkasan konteks grup
   * Tanggal dan waktu
7. Jika file duplikat terdeteksi, masukkan ke folder khusus `/Duplikat/`.

---

### ⚙️ **Contoh Fungsi di `ai_engine.py`**

```python
import requests, yaml

def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)

def analyze_files_with_gemini(file_summaries):
    cfg = load_config()
    headers = {"Authorization": f"Bearer {cfg['gemini_api_key']}"}
    payload = {
        "model": cfg["model"],
        "input": f"Kelompokkan file berikut:\n{file_summaries}"
    }
    response = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{cfg['model']}:generateContent",
        headers=headers, json=payload
    )
    return response.json()
```

---

### 🪶 **Tambahan**

* Tampilkan hasil grouping di GUI sebelum benar-benar memindahkan file (preview mode).
* Tambahkan tombol “Undo” (membatalkan pemindahan terakhir).
* Metadata disimpan dalam format yang mudah dibaca dan dapat di-export ke CSV.

---

### 📋 **Instruksi Akhir untuk Codex**

> Bangun seluruh aplikasi sesuai spesifikasi di atas, termasuk GUI, integrasi API Gemini, konfigurasi YAML, dan sistem grouping otomatis berbasis AI.
> Pastikan kode modular, mudah dibaca, dan siap dijalankan langsung dengan `python main.py`.


