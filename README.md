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

## Deployment ke Fujitsu

Eksperimen VQE di Fujitsu dijalankan melalui MPI/mpiQulacs dan tidak
memerlukan seluruh isi repository. Gunakan perintah allowlist berikut dari root
project lokal:

```bash
ssh qsim 'mkdir -p ~/deescalation-vqe/logs \
  ~/deescalation-vqe/notebooks/results/raw'

rsync -av --progress --relative \
  ./remote/job.sh \
  ./remote/run_quantum.py \
  ./remote/sim-preflight.job \
  ./remote/sim-hea.job \
  ./remote/sim-hva.job \
  ./src/qubo.py \
  ./notebooks/results/raw/qubo_ising_data.pkl \
  qsim:~/deescalation-vqe/
```

Perintah tersebut hanya mengirim file yang diperlukan untuk job Fujitsu:

```text
remote/job.sh
remote/run_quantum.py
remote/sim-preflight.job
remote/sim-hea.job
remote/sim-hva.job
src/qubo.py
notebooks/results/raw/qubo_ising_data.pkl
```

Notebook, PDF, README, konfigurasi lokal, visualisasi, hasil lama,
`__pycache__`, environment lokal, dan credential tidak dikirim ke Fujitsu.

Setelah upload, jalankan job dari login server Fujitsu:

```bash
cd ~/deescalation-vqe
sbatch remote/sim-preflight.job
```

Jalankan HEA dan HVA setelah preflight berhasil:

```bash
sbatch remote/sim-hea.job
sbatch remote/sim-hva.job
```

### Melihat hasil energi VQE

Setiap job menyimpan hasilnya sebagai file pickle (`.pkl`) di
`notebooks/results/raw/`. Gunakan job ID dari output `sbatch` untuk memilih
file yang sesuai:

```text
preflight-<JOB_ID>.pkl
vqe-hea-<JOB_ID>.pkl
vqe-hva-<JOB_ID>.pkl
```

Karena environment `qenv` dibuat untuk compute node, masuk terlebih dahulu ke
compute node dengan `salloc`, lalu dari root proyek jalankan perintah berikut
(ganti nama file sesuai job ID):

```bash
qenv/bin/python -c 'import pickle; r=pickle.load(open("notebooks/results/raw/preflight-<JOB_ID>.pkl", "rb")); print("final_energy =", r["final_energy"]); print("energy_history =", r["energy_history"])'
```

`final_energy` adalah energi akhir yang diperoleh optimizer, sedangkan
`energy_history` memuat energi setiap evaluasi. Untuk preflight, riwayat bisa
sangat pendek karena jumlah evaluasinya sengaja dibatasi. Hanya buka file
pickle yang dipercaya.

Jangan menggunakan `rsync ./` untuk deployment karena akan mengirim file
yang tidak diperlukan ke Fujitsu.

## Definisi Variabel

Definisi berikut dikelompokkan berdasarkan file tempat variabel digunakan.
Indeks `i` dan `j` umumnya menyatakan aktor, sedangkan `k` dan `ell` menyatakan
aksi atau qubit.

### `src/generate_network.py`

| Variabel | Definisi |
|---|---|
| `n_blocks` | Jumlah blok geopolitik. |
| `block_size` | Jumlah aktor dalam setiap blok. |
| `n` | Jumlah seluruh aktor, yaitu `n_blocks * block_size`. |
| `block` | Label blok untuk setiap aktor. |
| `p_in`, `p_out` | Probabilitas koneksi di dalam blok dan antarblok. |
| `p_neg` | Probabilitas koneksi antarblok bernilai negatif. |
| `j_in`, `j_out` | Rentang bobot interaksi di dalam blok dan antarblok. |
| `J` | Matriks interaksi; positif berarti kooperatif dan negatif berarti konflik. |
| `T` | Matriks tegangan yang dihasilkan oleh `max(0, -J)`. |

### `src/scenarios.py`

| Variabel | Definisi |
|---|---|
| `T` | Matriks tegangan dasar. |
| `Ts` | Matriks tegangan untuk satu skenario setelah diberi kejutan. |
| `block` | Label blok setiap aktor. |
| `delta_border` | Besar kenaikan tegangan untuk konflik perbatasan antarblok. |
| `delta_internal` | Besar kenaikan tegangan untuk konflik internal suatu blok. |
| `a`, `b` | Indeks dua blok bertetangga pada skenario perbatasan. |
| `mask`, `mask_a`, `mask_b` | Daftar indeks aktor yang berada dalam blok tertentu. |
| `weight` | Bobot probabilitas skenario; seluruh bobot dinormalisasi menjadi 1. |
| `scenarios` | Kumpulan seluruh skenario perbatasan dan internal. |

### `src/action.py`

| Variabel | Definisi |
|---|---|
| `m` | Jumlah aksi de-eskalasi. |
| `actions_per_block` | Jumlah jenis aksi yang tersedia untuk setiap blok. |
| `eff` | Daftar efektivitas enam jenis aksi. |
| `a_in`, `a_out` | Efektivitas aksi di dalam blok dan terhadap blok tetangga. |
| `a_type` | Indeks jenis aksi. |
| `alpha[k,i,j]` | Efektivitas aksi `k` pada tegangan antara aktor `i` dan `j`. |
| `left`, `right` | Blok tetangga kiri dan kanan dari blok yang sedang diproses. |

### `src/qubo.py`

| Variabel | Definisi |
|---|---|
| `costs[k]` | Biaya pemilihan aksi `k`. |
| `budget` | Batas atau target total biaya portofolio. |
| `eta` | Kekuatan penalti untuk pelanggaran anggaran. |
| `B_lin`, `D_quad`, `A_const` | Akumulasi komponen linear, kuadratik, dan konstan dari seluruh skenario. |
| `b_s`, `d_s`, `A_s` | Komponen linear, kuadratik, dan konstan untuk satu skenario. |
| `tij` | Tegangan antara aktor `i` dan `j`. |
| `a_vec` | Efektivitas seluruh aksi pada pasangan aktor `(i,j)`. |
| `q[k]` | Koefisien linear QUBO untuk aksi `k`. |
| `Q[k,ell]` | Koefisien kuadratik antara aksi `k` dan `ell`. |
| `const` | Konstanta fungsi objektif QUBO. |
| `x` | Vektor keputusan biner; `x[k] = 1` berarti aksi `k` dipilih. |
| `val` | Nilai fungsi objektif QUBO untuk satu `x`. |

```text
F(x) = const + sum_k q[k] x[k] + sum_{k<ell} Q[k,ell] x[k] x[ell].
```

### `src/ising.py`

| Variabel | Definisi |
|---|---|
| `z[k]` | Variabel spin Ising, dengan `z[k] = 1 - 2*x[k]`. |
| `g[k]` | Koefisien medan lokal `Z_k`. |
| `K[k,ell]` | Koefisien coupling `Z_k Z_ell`. |
| `c` | Konstanta energi Ising. |
| `qkl` | Koefisien QUBO `Q[k,ell]` yang sedang dikonversi. |
| `val` | Energi Ising untuk satu bitstring. |

### `src/qulacs_vqe.py`

| Variabel | Definisi |
|---|---|
| `m` | Jumlah qubit; sama dengan jumlah aksi. |
| `p`, `depth` | Jumlah lapisan ansatz. |
| `params` | Seluruh parameter rotasi yang sedang dioptimasi. |
| `gamma`, `gammas` | Parameter HVA untuk local field dan coupling `ZZ`. |
| `beta`, `betas` | Parameter HVA untuk mixer `RX`. |
| `gamma_tf` | Kekuatan transverse field pada observable energi. |
| `angle` | Sudut rotasi gate yang dihitung dari parameter dan koefisien Ising. |
| `obs`, `observable` | Hamiltonian yang nilai ekspektasinya diminimalkan. |
| `state` | State kuantum yang sedang disimulasikan. |
| `circuit` | Susunan gate HVA atau HEA yang diterapkan pada `state`. |
| `idx` | Posisi parameter HEA yang sedang dibaca. |
| `x0` | Parameter awal sebelum optimasi COBYLA. |
| `res` | Hasil optimasi; `.x` adalah parameter optimal dan `.fun` adalah energi minimum. |
| `energy_history` | Riwayat energi selama optimasi. |
| `n_shots` | Jumlah sampling bitstring. |
| `samples`, `X` | Hasil sampling; setiap baris merupakan satu portofolio biner. |
| `unique`, `ranked` | Portofolio unik dan hasil pengurutan berdasarkan objektif QUBO. |

### `src/baselines.py`

| Variabel | Definisi |
|---|---|
| `x` | Kandidat portofolio biner saat ini. |
| `field` | Perubahan lokal objektif yang dipengaruhi aksi lain. |
| `delta` | Perubahan nilai objektif apabila satu bit dibalik. |
| `rng` | Generator bilangan acak. |
| `temp` | Temperatur Simulated Annealing pada iterasi saat ini. |
| `fx`, `f_new` | Nilai objektif kandidat saat ini dan kandidat baru. |
| `best_x`, `best_fx` | Portofolio terbaik dan nilai objektif terbaik yang ditemukan. |

### `src/metrics.py`

| Variabel | Definisi |
|---|---|
| `action_selection` | Vektor keputusan biner aksi yang dievaluasi. |
| `risks` | Risiko residual portofolio pada setiap skenario. |
| `diminishing_factor` | Faktor sisa tegangan setelah seluruh aksi terpilih diterapkan. |
| `mean_risk` | Rata-rata risiko berbobot. |
| `worst_risk` | Risiko terbesar dari seluruh skenario. |
| `risk_std` | Simpangan baku risiko lintas skenario. |
| `f_alg` | Nilai objektif metode yang dievaluasi. |
| `f_exact_optimum` | Nilai objektif referensi atau optimum. |

### `src/plotting.py`

| Variabel | Definisi |
|---|---|
| `energy_history` | Data energi per evaluasi optimizer. |
| `portfolios_data` | Daftar pasangan nilai `budget` dan `risk`. |
| `vqe_portfolio_risks` | Risiko portofolio VQE pada seluruh skenario. |
| `baseline_risks` | Risiko metode klasik pada seluruh skenario. |
| `sampled_objectives` | Nilai objektif dari seluruh bitstring hasil sampling. |
| `save_path` | Lokasi opsional untuk menyimpan gambar. |

### Variabel pada notebook

| Variabel | Definisi |
|---|---|
| `data_n1`, `data_n2`, `data_n3` | Data hasil tahap notebook 1, 2, dan 3 yang dibaca dari pickle. |
| `vqe_res_hva`, `vqe_res_hea` | Hasil optimasi VQE untuk HVA dan HEA. |
| `vqe_x`, `sa_x`, `ls_x` | Portofolio terbaik dari VQE, Simulated Annealing, dan Local Search. |
| `vqe_robustness`, `sa_robustness`, `ls_robustness` | Metrik robustness dari ketiga metode. |
| `top_quantum_hva` | Portofolio HVA terbaik yang ditemukan melalui sampling. |
| `test_syauqi_bits` | Bitstring acak untuk menguji kesetaraan nilai QUBO dan Ising; bukan variabel khusus algoritma. |

## Log Perubahan (Change Log)
Anda dapat membaca histori teknis pembaruan, perbaikan bug, maupun penambahan fitur terkait integrasi penuh *codebase* pada file `CHANGELOG.md`.
