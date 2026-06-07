# De-escalation War Portfolio Optimization

Proyek ini bertujuan untuk menyelesaikan masalah optimasi portofolio de-eskalasi menggunakan formulasi Quadratic Unconstrained Binary Optimization (QUBO) dan Model Ising. Evaluasi solusi diukur dan dibandingkan secara komprehensif menggunakan simulator Kuantum (VQE dengan arsitektur HVA & HEA) serta menggunakan pendekatan klasik baseline (Simulated Annealing dan Local Search).

## Struktur Direktori Utama
- `src/`: Kumpulan modul pendukung proyek.
  - `generate_network.py` & `scenarios.py`: Membuat graf / jaringan dan mendefinisikan simulasi tegangan.
  - `qubo.py` & `ising.py`: Translasi masalah ke format matematika QUBO dan Hamiltonian Ising.
  - `qulacs_vqe.py`: Implementasi optimasi algoritma kuantum VQE menggunakan *Qulacs*.
  - `baselines.py`: Penyelesaian klasik (Local Search & Simulated Annealing).
  - `metrics.py`: Metrik analitik (*Budget Utilization*, *Robustness* antar skenario, *Optimality gap*).
  - `plotting.py`: Modul visualisasi data kuantum dan metrik portofolio.
- `notebooks/`: Pipeline eksperimen berurut dalam bentuk jupyter notebook.
- `configs/`: Tempat meletakkan file konfigurasi parameter simulasi.

## Alur Pipeline Eksperimen
1. **`01_generate_instance.ipynb`**: Tahap awal pembuatan jaringan interaksi (network), matriks tensi, dan penyusunan skenario simulasi de-eskalasi.
2. **`02_verify_qubo.ipynb`**: Membangun bentuk optimasi matematis QUBO dan mengonversinya menjadi format Hamiltonian Ising.
3. **`03_run_vqe.ipynb`**: Menjalankan eksperimen optimasi VQE menggunakan algoritma HVA dan membandingkannya dengan pendekatan HEA. Menyediakan plot konvergensi energi kuantum serta distribusi histogram pencarian portofolio terbaik.
4. **`04_compare_baseline.ipynb`**: Komparasi mendalam antara algoritma VQE dengan pencari konvensional (Simulated Annealing & Local Search). Fokus evaluasi tidak hanya pada nilai fungsi objektif, namun mencakup seberapa banyak alokasi biaya/budget yang terpakai dan bagaimana tingkat keandalan (*robustness*) portofolio jika diuji dengan berbagai *stress scenarios*.

## Log Perubahan (Change Log)
Anda dapat membaca histori teknis pembaruan, perbaikan bug, maupun penambahan fitur terkait integrasi penuh *codebase* pada file `CHANGELOG.md`.
