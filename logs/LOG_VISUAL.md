# Visualisasi Log Perubahan Kode

File ini dibuat secara otomatis oleh `logger.py`. File ini memvisualisasikan data dari `changelog.json`.

| Waktu | File | Tipe | Nama | Alasan/Tujuan |
|---|---|---|---|---|
| 2026-06-06 03:40:07 | `src/qulacs_vqe.py` | **Function** | `evaluate_energy_hea` | Menghitung nilai ekspektasi energi khusus untuk arsitektur HEA. |
| 2026-06-06 03:40:07 | `src/qulacs_vqe.py` | **Function** | `build_hea_circuit` | Membangun sirkuit kuantum dengan arsitektur HEA (Hardware Efficient Ansatz) standar. |
| 2026-06-06 03:40:07 | `src/qulacs_vqe.py` | **Function** | `evaluate_energy_hva` | Menghitung nilai ekspektasi (energi) dari sirkuit HVA terhadap observable. |
| 2026-06-06 03:40:06 | `src/qulacs_vqe.py` | **Function** | `build_hva_circuit` | Membangun sirkuit kuantum berdasarkan arsitektur Hardware-efficient Ansatz (HVA). |
| 2026-06-06 03:39:23 | `src/qulacs_vqe.py` | **Function** | `build_observable` | Membangun operator observable Hamiltonian Ising berdasarkan matriks tension dan interaksi. |
| 2026-06-06 03:39:23 | `src/qulacs_vqe.py` | **Function** | `best_sampled_portfolios` | Memfilter dan mengurutkan sampel bitstring untuk mendapatkan top K portofolio dengan nilai objektif terbaik. |
| 2026-06-06 03:39:23 | `src/qulacs_vqe.py` | **Function** | `sample_hva_portfolios` | Melakukan sampling dari state kuantum (HVA) yang sudah dioptimasi untuk mendapatkan bitstring portofolio. |
| 2026-06-06 03:39:23 | `src/qulacs_vqe.py` | **Function** | `run_hva_vqe` | Fungsi utama untuk mengeksekusi optimasi VQE menggunakan Hardware-efficient Ansatz (HVA). |
| 2026-06-06 03:30:30 | `src/qulacs_vqe.py` | **Function** | `sample_hea_portfolios` | Mengekstrak hasil bitstring terbaik dari Ansatz HEA setelah model VQE optimal. |
| 2026-06-06 03:30:15 | `src/qulacs_vqe.py` | **Function** | `run_hea_vqe` | Fungsi pembungkus untuk menjalankan optimasi VQE menggunakan Hardware-Efficient Ansatz (HEA), untuk eksperimen pembanding. |
| 2026-06-06 03:30:00 | `src/qulacs_vqe.py` | **Variable** | `energy_history` | Menyimpan riwayat penurunan nilai energi tiap iterasi optimasi VQE agar konvergensinya dapat divisualisasikan. |
