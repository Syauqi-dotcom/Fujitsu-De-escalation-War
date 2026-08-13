# Cara Menyambungkan dan Menjalankan Proyek di Fujitsu Quantum Simulator

Dokumen ini adalah panduan kerja untuk menjalankan proyek **De-escalation War Portfolio Optimization** di Fujitsu Quantum Simulator2.

Bahasanya sengaja dibuat santai supaya gampang diikuti. Tapi semua nama command, file, partisi Slurm, dan aturan MPI tetap mengikuti dokumen resmi:

- `docs_qsc2025-26_en.pdf`;
- Fujitsu Quantum Simulator2 v1.6.3;
- QSC2025-26, rilis 8 Mei 2026.

Password PDF tidak ditulis di sini. Simpan password, private key, dan credential lain di tempat privat.

> **Aturan penting:** selama QSC2025-26, job harus masuk ke partisi `Batch` memakai `sbatch`. Jangan pakai `IntrHPC` atau `isbatch` karena sedang dinonaktifkan untuk peserta QSC.

## Mulai di sini — runbook dari lokal sampai selesai

Bagian ini adalah urutan paling singkat yang tetap aman untuk menjalankan eksperimen dari awal. Bagian-bagian bernomor setelahnya menjelaskan setiap langkah dengan lebih detail.

Alur lengkapnya:

```text
siapkan environment lokal
    → cek sintaks
    → buat dan validasi input QUBO/Ising
    → tes circuit kecil di lokal
    → cek SSH
    → upload proyek
    → siapkan qenv di compute node
    → preflight
    → validasi preflight
    → HEA
    → validasi HEA
    → HVA
    → validasi HVA
    → download hasil
    → analisis akhir di lokal
```

### Tahap A — siapkan environment lokal

Masuk ke root proyek:

```bash
cd /home/quantoqi/Documents/Fujistsu/De-escalation_War
```

Aktifkan environment Python lokal yang biasa dipakai proyek. Jika belum ada, buat environment di luar direktori proyek agar file environment tidak ikut ter-upload:

```bash
python3 -m venv ../deescalation-local-env
source ../deescalation-local-env/bin/activate
python -m pip install --upgrade pip
python -m pip install numpy scipy matplotlib jupyter pyyaml qulacs
```

Environment lokal memakai `qulacs` biasa. Environment Fujitsu pada Tahap F memakai `mpiQulacs`; jangan meng-upload environment lokal ke Fujitsu.

Cek package lokal:

```bash
python -c "import numpy, scipy, matplotlib, qulacs; print('local environment OK')"
```

### Tahap B — cek kode secara statis di lokal

Cek semua file Python tanpa menjalankan simulasi:

```bash
python - <<'PY'
import ast
from pathlib import Path

for path in sorted([*Path("src").glob("*.py"), *Path("remote").glob("*.py")]):
    ast.parse(path.read_text(), filename=str(path))
    print("OK", path)
PY
```

Cek file shell dan keberadaan direktori yang sudah dipakai proyek:

```bash
bash -n remote/job.sh remote/sim-preflight.job remote/sim-hea.job remote/sim-hva.job
test -d notebooks/results/raw
test -d logs
test -x remote/job.sh
```

Semua command harus selesai dengan exit code 0.

### Tahap C — buat input dan lakukan tes numerik lokal

Jalankan notebook pembentuk instance dan QUBO/Ising. Hasil notebook eksekusi diletakkan di `/tmp` supaya root proyek tidak dipenuhi file tambahan:

```bash
PYTHONPATH="$PWD" jupyter nbconvert --to notebook --execute \
  --ExecutePreprocessor.timeout=600 \
  --output-dir /tmp \
  --output 01_generate_instance.executed.ipynb \
  notebooks/01_generate_instance.ipynb

PYTHONPATH="$PWD" jupyter nbconvert --to notebook --execute \
  --ExecutePreprocessor.timeout=600 \
  --output-dir /tmp \
  --output 02_verify_qubo.executed.ipynb \
  notebooks/02_verify_qubo.ipynb
```

Tahap lokal ini tidak memakai node Fujitsu dan tidak dihitung sebagai node-hour Fujitsu.

Validasi bentuk data, nilai hingga, dan kesetaraan energi QUBO–Ising:

```bash
python - <<'PY'
import pickle
import numpy as np
from src.qubo import qubo_value
from src.ising import ising_value_from_bits

path = "notebooks/results/raw/qubo_ising_data.pkl"
with open(path, "rb") as file:
    data = pickle.load(file)

required = {"K", "g", "q", "Q", "const", "c_ising"}
assert required <= data.keys(), required - data.keys()
assert data["K"].shape == (30, 30)
assert data["Q"].shape == (30, 30)
assert data["g"].shape == (30,)
assert data["q"].shape == (30,)
for key in required:
    assert np.isfinite(data[key]).all(), f"{key} mengandung NaN/inf"

rng = np.random.default_rng(123)
for _ in range(20):
    bits = rng.integers(0, 2, size=30)
    qubo_energy = qubo_value(bits, data["q"], data["Q"], data["const"])
    ising_energy = ising_value_from_bits(
        bits, data["K"], data["g"], data["c_ising"]
    )
    np.testing.assert_allclose(qubo_energy, ising_energy, atol=1e-8, rtol=0)

print("local QUBO/Ising validation OK")
PY
```

Tes circuit kecil 4-qubit. Tes ini hanya memeriksa API dan alur circuit; jangan menjalankan VQE 30-qubit penuh di komputer lokal:

```bash
python - <<'PY'
import numpy as np
from src.qulacs_vqe import build_observable, evaluate_energy_hva

qubits = 4
K = np.zeros((qubits, qubits))
K[0, 1] = K[1, 0] = 0.25
g = np.array([0.1, -0.2, 0.3, -0.1])
observable = build_observable(K, g, gamma_tf=0.2)
energy = evaluate_energy_hva(
    np.array([0.1, 0.2]), K, g, observable
)
assert np.isfinite(energy)
print("local circuit smoke test OK; energy =", energy)
PY
```

Catat hash input yang akan dikirim:

```bash
sha256sum notebooks/results/raw/qubo_ising_data.pkl
```

Jangan lanjut jika notebook gagal, bentuk data salah, terdapat `NaN/inf`, energi tidak sama, atau circuit smoke test gagal.

### Tahap D — cek koneksi Fujitsu

Pastikan komputer memakai static global IP yang sudah didaftarkan, lalu jalankan:

```bash
ssh -G qsim >/dev/null
ssh qsim
```

Di login server, cek:

```bash
hostname
sinfo
sinfo -T
```

Kembali ke komputer lokal dengan `exit` sebelum melakukan upload.

### Tahap E — upload proyek dari lokal

Jalankan dari root proyek lokal:

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

Perintah tersebut hanya mengirim:

```text
remote/job.sh
remote/run_quantum.py
remote/sim-preflight.job
remote/sim-hea.job
remote/sim-hva.job
src/qubo.py
notebooks/results/raw/qubo_ising_data.pkl
```

Notebook, PDF, README, konfigurasi lokal, visualisasi, hasil lama, dan
environment lokal tidak dikirim.

Masuk kembali dan pastikan file penting tersedia:

```bash
ssh qsim
cd ~/deescalation-vqe
test -d logs
test -d notebooks/results/raw
test -x remote/job.sh
test -r remote/run_quantum.py
test -r notebooks/results/raw/qubo_ising_data.pkl
sha256sum notebooks/results/raw/qubo_ising_data.pkl
```

Hash remote harus sama persis dengan hash lokal.

### Tahap F — siapkan environment mpiQulacs di compute node

Environment remote hanya perlu dibuat sekali. Dari login server, minta compute node interaktif:

```bash
salloc -N 1 -p Interactive --time=02:00:00
```

Alokasi setup ini memakai 1 node dengan batas maksimum 2 jam, yaitu maksimum 2 node-hour. Setelah `qenv` tersedia, tahap ini dapat dilewati pada eksperimen berikutnya.

Setelah prompt menunjukkan compute node `fx-...`:

```bash
cd ~/deescalation-vqe
python3 -m venv qenv
source qenv/bin/activate
python -m pip install --upgrade pip wheel
python -m pip install mpi4py numpy scipy mpiQulacs
python -c "import mpi4py, numpy, scipy, qulacs; print('remote environment OK')"
python -m pip freeze > requirements-remote.lock.txt
deactivate
exit
```

Jika `qenv` sudah tersedia, jangan membuatnya ulang. Cukup aktifkan dan jalankan pengecekan import di compute node.

### Tahap G — jalankan dan validasi preflight

Dari login server dan root proyek:

```bash
cd ~/deescalation-vqe
sbatch remote/sim-preflight.job
```

Resource preflight: 1 node, 48 core, batas 30 menit, maksimum 0,5 node-hour.

Ganti angka contoh dengan job ID yang diberikan `sbatch`, lalu pantau:

```bash
PREFLIGHT_JOBID=123456
squeue -j "${PREFLIGHT_JOBID}"
sacct -j "${PREFLIGHT_JOBID}" \
  -o JobID,JobName%20,NNodes,AllocCPUS,Elapsed,State,ExitCode
cat "logs/preflight-${PREFLIGHT_JOBID}.out"
cat "logs/preflight-${PREFLIGHT_JOBID}.err"
```

Preflight harus memenuhi seluruh syarat berikut:

- `State=COMPLETED`;
- `ExitCode=0:0`;
- stderr kosong;
- `world_size=4`;
- device `multi-cpu`;
- log memuat `optimizer selesai` dan `hasil disimpan`;
- file `notebooks/results/raw/preflight-${PREFLIGHT_JOBID}.pkl` tersedia.

Jika ada satu syarat yang gagal, berhenti dan perbaiki masalah sebelum melanjutkan.

### Tahap H — jalankan dan validasi HEA

HEA dijalankan lebih dahulu karena circuit per evaluasinya lebih ringan:

```bash
sbatch remote/sim-hea.job
```

Resource HEA: 1 node, 48 core, batas 8 jam, maksimum 8 node-hour.

Ganti angka contoh dengan job ID HEA, kemudian:

```bash
HEA_JOBID=123457
squeue -j "${HEA_JOBID}"
sacct -j "${HEA_JOBID}" \
  -o JobID,JobName%20,NNodes,AllocCPUS,Elapsed,State,ExitCode
cat "logs/hea-${HEA_JOBID}.err"
test -r "notebooks/results/raw/vqe-hea-${HEA_JOBID}.pkl"
```

HEA harus `COMPLETED`, exit code `0:0`, stderr kosong, device `multi-cpu`, dan menghasilkan file pickle.

### Tahap I — jalankan dan validasi HVA

Setelah HEA berhasil:

```bash
sbatch remote/sim-hva.job
```

Resource HVA default: 2 node, 96 core total, batas 8 jam, maksimum 16 node-hour.

Ganti angka contoh dengan job ID HVA, kemudian:

```bash
HVA_JOBID=123458
squeue -j "${HVA_JOBID}"
sacct -j "${HVA_JOBID}" \
  -o JobID,JobName%20,NNodes,AllocCPUS,Elapsed,State,ExitCode
cat "logs/hva-${HVA_JOBID}.err"
test -r "notebooks/results/raw/vqe-hva-${HVA_JOBID}.pkl"
```

HVA harus memenuhi kriteria keberhasilan yang sama dengan HEA. Jika preflight mencatat `native_zz=False`, pertimbangkan konfigurasi fallback 4 node:

```bash
sbatch -N 4 -t 12:00:00 remote/sim-hva.job
```

### Tahap J — download seluruh hasil ke lokal

Keluar dari Fujitsu, kemudian jalankan dari root proyek lokal. Ganti angka contoh dengan job ID sebenarnya:

```bash
PREFLIGHT_JOBID=123456
HEA_JOBID=123457
HVA_JOBID=123458

rsync -av --progress \
  "qsim:~/deescalation-vqe/notebooks/results/raw/preflight-${PREFLIGHT_JOBID}.pkl" \
  notebooks/results/raw/

rsync -av --progress \
  "qsim:~/deescalation-vqe/notebooks/results/raw/vqe-hea-${HEA_JOBID}.pkl" \
  notebooks/results/raw/

rsync -av --progress \
  "qsim:~/deescalation-vqe/notebooks/results/raw/vqe-hva-${HVA_JOBID}.pkl" \
  notebooks/results/raw/

rsync -av --progress \
  qsim:~/deescalation-vqe/logs/ \
  logs/
```

### Tahap K — periksa hasil dan jalankan analisis akhir lokal

Aktifkan kembali environment lokal, lalu periksa metadata hasil HVA:

```bash
export HVA_JOBID=123458
python - <<'PY'
import os
import pickle

path = f"notebooks/results/raw/vqe-hva-{os.environ['HVA_JOBID']}.pkl"
with open(path, "rb") as file:
    result = pickle.load(file)

required = {
    "input_sha256", "ansatz", "depth", "optimizer_success",
    "final_energy", "rank_count", "node_count", "qulacs_device",
    "wall_time_seconds", "ranked_portfolios", "resource_estimate",
}
assert required <= result.keys(), required - result.keys()
assert result["ansatz"] == "hva"
assert result["qulacs_device"] == "multi-cpu"
assert result["ranked_portfolios"]
print("result metadata OK")
print("wall time:", result["wall_time_seconds"], "seconds")
print("resource:", result["resource_estimate"])
PY
```

Salin hasil HVA terpilih ke nama yang dibaca notebook evaluasi:

```bash
cp "notebooks/results/raw/vqe-hva-${HVA_JOBID}.pkl" \
  notebooks/results/raw/vqe_results.pkl
```

Jalankan perbandingan VQE dengan baseline klasik:

```bash
PYTHONPATH="$PWD" jupyter nbconvert --to notebook --execute \
  --ExecutePreprocessor.timeout=1200 \
  --output-dir /tmp \
  --output 04_compare_baseline.executed.ipynb \
  notebooks/04_compare_baseline.ipynb
```

Eksperimen dinyatakan selesai jika:

- seluruh job yang dipakai berstatus `COMPLETED` dengan exit code `0:0`;
- hash input lokal, remote, dan metadata hasil sama;
- device seluruh hasil remote adalah `multi-cpu`;
- file hasil HEA dan HVA dapat dibaca;
- `ranked_portfolios` tidak kosong;
- notebook evaluasi akhir selesai tanpa error;
- log dan job ID disimpan untuk reproduksibilitas.

Resource maksimum untuk eksekusi pertama adalah 26,5 node-hour: setup environment 2, preflight 0,5, HEA 8, dan HVA 16 node-hour. Setelah `qenv` tersedia, pengulangan eksperimen membutuhkan maksimum 24,5 node-hour. Penjelasan rinci dan cara menghitung pemakaian aktual ada di Bagian 17.

## 1. Gambaran gampangnya

Kamu tidak bisa SSH langsung dari laptop ke compute node Fujitsu. Jalurnya seperti ini:

```text
Laptop/PC kamu
    |
    | ssh qsim
    v
Jump server Fujitsu
    |
    v
Login server (loginvm-XXX)
    |
    | salloc atau sbatch
    v
Compute node A64FX (fx-XX-XX-XX)
    |
    v
mpiQulacs menjalankan simulasi quantum circuit
```

Penjelasan singkat:

- **jump server** cuma pintu masuk;
- **login server** dipakai untuk upload file, menyiapkan job, dan menjalankan command Slurm;
- **compute node** adalah tempat simulasi benar-benar berjalan;
- **Slurm** adalah sistem yang membagikan compute node ke pengguna;
- **mpiQulacs** adalah simulator quantum yang jalan paralel di beberapa proses/node.

Ini adalah quantum simulator berbasis cluster A64FX, bukan koneksi langsung ke QPU fisik.

## 2. Kondisi proyek sekarang

Eksperimen proyek memakai 30 variabel aksi, jadi target utamanya adalah simulasi **30 qubit**.

Alur kerjanya:

```text
Lokal                                         Fujitsu
-----                                         -------
01_generate_instance.ipynb
02_verify_qubo.ipynb
  menghasilkan qubo_ising_data.pkl   ----->  run_quantum.py
                                                  |
                                                  | VQE + sampling
                                                  v
04_compare_baseline.ipynb              <----- vqe_results-<JOBID>.pkl
```

Yang dikerjakan lokal:

- membuat network dan scenario;
- membuat QUBO dan Hamiltonian Ising;
- mengecek konsistensi energi;
- menjalankan baseline klasik;
- membuat plot dan laporan.

Yang dikerjakan di Fujitsu:

- seluruh loop VQE;
- optimizer COBYLA;
- evaluasi quantum state;
- sampling;
- pencatatan runtime dan metadata MPI.

Jangan menjalankan optimizer VQE di laptop lalu mengirim evaluasi satu per satu ke Fujitsu. Optimizer bisa memanggil simulator ratusan kali, jadi optimizer dan simulator harus berada di job yang sama.

### File eksekusi yang tersedia

Proyek sekarang sudah menyediakan file utama untuk eksekusi Slurm:

```text
remote/run_quantum.py
remote/job.sh
remote/sim-preflight.job
remote/sim-hea.job
remote/sim-hva.job
notebooks/results/raw/qubo_ising_data.pkl
```

Kode `src/qulacs_vqe.py` dan runner remote sudah mendukung mpiQulacs. Detail implementasinya ada di bagian 7.

## 3. Perbaiki SSH di komputer lokal

Konfigurasi `qsim` dan `qsim-gw` sudah ada di `~/.ssh/config`. Tapi pada pemeriksaan terakhir, SSH berhenti karena permission file sistem salah:

```text
Bad owner or permissions on /etc/ssh/ssh_config.d/20-systemd-ssh-proxy.conf
```

Perbaiki dengan:

```bash
sudo chown root:root \
  /etc/ssh \
  /etc/ssh/ssh_config.d \
  /etc/ssh/ssh_config.d/20-systemd-ssh-proxy.conf

sudo chmod 755 /etc/ssh /etc/ssh/ssh_config.d
sudo chmod 644 /etc/ssh/ssh_config.d/20-systemd-ssh-proxy.conf
chmod 600 ~/.ssh/config
```

Cek apakah konfigurasi SSH sudah bisa dibaca:

```bash
ssh -G qsim >/dev/null
```

Kalau tidak ada error, coba login:

```bash
ssh qsim
```

Prompt yang benar kira-kira seperti ini:

```text
[username@loginvm-XXX ~]$
```

Kalau prompt masih menunjukkan jump server, berarti kamu belum sampai ke login server.

### Syarat koneksi Fujitsu

Fujitsu membutuhkan:

- username yang sudah didaftarkan;
- public key Ed25519;
- static global IP address;
- port SSH yang diberikan Fujitsu.

Koneksi dari IP lain akan ditolak. Pastikan kamu memakai jaringan dengan global IP yang sudah didaftarkan.

### Bentuk konfigurasi SSH

Kurang lebih bentuk `~/.ssh/config`-nya seperti ini:

```sshconfig
Host qsim-gw
    HostName 125.206.100.37
    Port <PORT_DARI_FUJITSU>
    User <USERNAME_DARI_FUJITSU>
    IdentityFile ~/.ssh/id_ed25519

Host qsim
    HostName login-server
    User <USERNAME_DARI_FUJITSU>
    IdentityFile ~/.ssh/id_ed25519
    ProxyJump qsim-gw
```

Dokumen Fujitsu memakai `ProxyCommand`. `ProxyJump` di atas adalah bentuk OpenSSH modern dengan alur yang sama. Kalau konfigurasi dari Fujitsu sudah bekerja, tidak perlu diganti.

## 4. Cek akses ke compute node

Setelah masuk ke login server, cek kondisi cluster:

```bash
hostname
sinfo
sinfo -T
```

Arti command:

- `hostname`: memastikan kamu berada di server yang benar;
- `sinfo`: melihat partisi dan ketersediaan node;
- `sinfo -T`: melihat jadwal maintenance/reservation.

Untuk masuk sementara ke satu compute node:

```bash
salloc -N 1 -p Interactive --time=00:30:00
```

Kalau berhasil, prompt berubah menjadi kira-kira:

```text
[username@fx-XX-XX-XX ~]$
```

Cek lagi:

```bash
hostname
```

Selesai mengecek compute node, keluar supaya resource langsung dilepas:

```bash
exit
```

Jangan membiarkan alokasi `Interactive` menyala kalau sudah tidak dipakai.

## 5. Siapkan data proyek di lokal

Masuk ke root proyek:

```bash
cd /home/quantoqi/Documents/Fujistsu/De-escalation_War
test -d notebooks/results/raw
test -d logs
```

Jalankan notebook secara berurutan:

```bash
PYTHONPATH="$PWD" jupyter nbconvert --to notebook --execute \
  notebooks/01_generate_instance.ipynb \
  --output 01_generate_instance.executed.ipynb

PYTHONPATH="$PWD" jupyter nbconvert --to notebook --execute \
  notebooks/02_verify_qubo.ipynb \
  --output 02_verify_qubo.executed.ipynb
```

File yang harus muncul:

```text
notebooks/results/raw/instance_data.pkl
notebooks/results/raw/qubo_ising_data.pkl
```

Cek:

```bash
ls -lh notebooks/results/raw/instance_data.pkl
ls -lh notebooks/results/raw/qubo_ising_data.pkl
sha256sum notebooks/results/raw/qubo_ising_data.pkl
```

Sebelum upload, pastikan:

- `K` dan `Q` berukuran `(30, 30)`;
- `g` dan `q` berukuran `(30,)`;
- tidak ada `NaN` atau infinity;
- energi QUBO dan Ising cocok untuk bitstring uji yang sama;
- bug HVA sudah diperbaiki;
- seed eksperimen sudah ditentukan.

## 6. Upload proyek ke Fujitsu

Jalankan dari komputer lokal:

```bash
cd /home/quantoqi/Documents/Fujistsu/De-escalation_War

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

Jangan menambahkan `--delete` kecuali kamu memang ingin menghapus file remote yang tidak ada di lokal.

Untuk update berikutnya, jalankan kembali perintah allowlist upload yang sama.

Setelah upload, masuk dan cek file remote:

```bash
ssh qsim
cd ~/deescalation-vqe
test -d logs
test -d notebooks/results/raw
sha256sum notebooks/results/raw/qubo_ising_data.pkl
```

Hash remote harus sama dengan hash lokal.

## 7. Perubahan kode yang wajib dilakukan

### 7.1. Perbaiki rotasi ZZ pada HVA

Versi lama memakai `beta` untuk interaksi ZZ:

```python
angle = 2.0 * beta * K[k, ell]
```

Implementasi sekarang sudah memakai `gamma`:

```python
angle = 2.0 * gamma * K[k, ell]
```

`beta` tetap dipakai untuk mixer RX:

```python
circuit.add_RX_gate(k, 2.0 * beta)
```

Preflight memastikan implementasi ini dapat dijalankan pada mpiQulacs target.

### 7.2. Pakai state yang mendukung MPI

Kode sekarang membuat state seperti ini:

```python
state = QuantumState(m)
```

Untuk runner Fujitsu, ubah semua pembuatan state menjadi:

```python
state = QuantumState(m, use_multi_cpu=True)
```

Perubahan ini dibutuhkan di:

- evaluasi energi HVA;
- evaluasi energi HEA;
- sampling HVA;
- sampling HEA.

Cek device yang benar-benar dipakai:

```python
device = state.get_device_name()
```

Nilainya bisa:

- `cpu`: state belum dibagi antar-rank;
- `multi-cpu`: state sudah dibagi antar-rank.

Simpan nilai tersebut di metadata hasil.

### 7.3. Impor MPI

Runner harus mengimpor MPI sebelum memakai simulator:

```python
from mpi4py import MPI
from qulacs import QuantumCircuit, QuantumState

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
world_size = comm.Get_size()
```

Dokumen Fujitsu menyebut import MPI yang hilang sebagai salah satu penyebab segmentation fault.

### 7.4. Semua rank harus menjalankan alur yang sama

Gampangnya, setiap rank adalah salinan program yang berjalan bersamaan. Jadi semua rank harus:

- membuat circuit yang sama;
- memakai parameter yang sama;
- memakai seed yang sama;
- memanggil simulator dalam urutan yang sama;
- menjalankan optimizer yang sama;
- melakukan sampling yang sama.

Yang hanya boleh dilakukan rank 0:

- menampilkan progres normal;
- membuat plot;
- merangking portofolio;
- menulis file hasil.

Pola yang benar:

```python
samples = state.sampling(n_shots, seed)

if rank == 0:
    save_results(samples)
```

Pola yang salah:

```python
if rank == 0:
    samples = state.sampling(n_shots, seed)
```

Pada pola salah, cuma rank 0 yang memanggil simulator. Rank lain akan punya urutan MPI berbeda dan job bisa hang atau gagal.

### 7.5. Sampling harus punya seed

Gunakan:

```python
samples = state.sampling(n_shots, seed)
```

Jangan hanya memakai:

```python
samples = state.sampling(n_shots)
```

Seed yang jelas membuat hasil lebih gampang diulang dan dibandingkan.

## 8. Buat environment di compute node

Masuk ke login server:

```bash
ssh qsim
```

Minta satu compute node:

```bash
salloc -N 1 -p Interactive --time=02:00:00
```

Di compute node:

```bash
cd ~/deescalation-vqe
python3 -m venv qenv
source qenv/bin/activate

pip install --upgrade pip wheel
pip install mpi4py numpy scipy mpiQulacs
```

Cek import:

```bash
python -c "import mpi4py, numpy, scipy, qulacs; print('environment OK')"
python -m pip show mpiQulacs mpi4py numpy scipy
```

Simpan versi package:

```bash
python -m pip freeze > requirements-remote.lock.txt
```

Lalu keluar:

```bash
deactivate
exit
```

`mpiQulacs` diimpor dengan nama `qulacs`. Jangan menginstal package `qulacs` biasa di environment yang sama.

Gunakan satu venv untuk proyek ini. Satu venv bisa berisi puluhan ribu file, sedangkan shared filesystem dibatasi sekitar 1,2 juta objek per grup.

## 9. File yang dibutuhkan untuk Slurm

Struktur remote yang dipakai:

```text
~/deescalation-vqe/
├── qenv/
├── src/
│   └── qulacs_vqe.py
├── remote/
│   ├── run_quantum.py
│   ├── job.sh
│   ├── sim-preflight.job
│   ├── sim-hva.job
│   └── sim-hea.job
├── notebooks/
│   └── results/
│       └── raw/
│           └── qubo_ising_data.pkl
└── logs/
```

Fungsi masing-masing:

| File | Dipakai untuk apa |
| --- | --- |
| `run_quantum.py` | Menjalankan VQE dan sampling pada semua rank MPI |
| `job.sh` | Mengaktifkan venv dan mengatur MPI, thread, dan NUMA |
| `sim-preflight.job` | Validasi jalur produksi dengan iterasi dan shot minimum |
| `sim-hva.job` | Menjalankan produksi HVA |
| `sim-hea.job` | Menjalankan produksi HEA secara terpisah |
| `qubo_ising_data.pkl` | Input QUBO/Ising 30 qubit |
| `notebooks/results/raw/` | Lokasi input dan hasil pickle yang sudah tersedia |
| `logs/` | Lokasi standard output dan standard error Slurm |

Atur permission:

```bash
chmod 700 remote/job.sh
chmod 600 remote/*.job remote/run_quantum.py
```

`job.sh` harus executable. File `.job` tidak perlu executable karena dibaca oleh `sbatch`.

Cek line ending:

```bash
file remote/job.sh remote/*.job
sed -i 's/\r$//' remote/job.sh remote/*.job
```

## 10. Isi `job.sh`

`job.sh` bukan file yang meminta node. Tugasnya adalah menyiapkan environment di setiap rank setelah Slurm memberikan node.

Simpan sebagai `remote/job.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

export UCX_IB_MLX5_DEVX=no
export OMP_PROC_BIND=TRUE

local_size=${OMPI_COMM_WORLD_LOCAL_SIZE:?OMPI_COMM_WORLD_LOCAL_SIZE tidak tersedia}
local_rank=${OMPI_COMM_WORLD_LOCAL_RANK:?OMPI_COMM_WORLD_LOCAL_RANK tidak tersedia}
export OMP_NUM_THREADS=1
export QULACS_NUM_THREADS=48

source "$1/bin/activate"
shift

if [ -z "${LD_PRELOAD:-}" ]; then
    export LD_PRELOAD=/lib64/libgomp.so.1
else
    export LD_PRELOAD=/lib64/libgomp.so.1:"$LD_PRELOAD"
fi

command_name=$1
shift

if [ "$local_size" -eq 1 ]; then
    numactl -m 0-3 -N 0-3 "$command_name" "$@"
elif [ "$local_size" -eq 4 ]; then
    numactl -N "$local_rank" -m "$local_rank" "$command_name" "$@"
else
    "$command_name" "$@"
fi
```

Kenapa ada setting tersebut:

- `OMP_NUM_THREADS=1` dan `QULACS_NUM_THREADS=48` mengikuti contoh resmi
  Fujitsu Quantum Simulator2 v1.6.3;
- mpiQulacs mengelola paralelisasi simulator pada 48 core A64FX;
- jangan membagi `QULACS_NUM_THREADS` menjadi `48 / jumlah-rank`; itu bukan
  konfigurasi runtime pada contoh resmi Fujitsu;
- `LD_PRELOAD`: workaround resmi untuk masalah `libgomp`;
- `numactl`: mengikat rank ke area memori/NUMA yang sesuai.

Validasi:

```bash
chmod 700 remote/job.sh
bash -n remote/job.sh
```

Kalau wrapper resmi di bawah ini berubah, pakai versi Fujitsu sebagai acuan terbaru:

```text
/home/share/developer/manual_examples/QSC2025/example/job.sh
```

Tidak perlu menjalankan proyek contoh di folder tersebut.

## 11. Ketentuan `run_quantum.py`

`run_quantum.py` adalah entry point utama proyek. File ini harus bisa dijalankan tanpa notebook dan tanpa GUI.

### Argumen minimum

```text
--input <path-pickle>
--output <path-pickle>
--ansatz <hva|hea>
--depth <integer-positif>
--shots <integer-positif>
--seed <integer>
--maxiter <integer-positif>
```

### Yang harus dilakukan runner

1. Impor `mpi4py` dan ambil rank/world size.
2. Baca input QUBO/Ising.
3. Cek dimensi dan nilai input.
4. Buat state dengan `use_multi_cpu=True`.
5. Jalankan optimizer pada semua rank.
6. Jalankan sampling pada semua rank.
7. Batasi print dan penulisan file ke rank 0.
8. Simpan hasil sebagai dictionary biasa.
9. Keluar dengan status nonzero kalau terjadi error.

Runner harus menolak input kalau:

- key `K`, `g`, `q`, `Q`, atau `const` tidak ada;
- matriks tidak persegi;
- panjang vector tidak cocok;
- ada `NaN` atau infinity;
- depth, shots, atau maxiter tidak positif;
- nama ansatz tidak dikenal;
- path output sama dengan path input.

### Isi hasil minimum

File hasil sebaiknya berisi:

```text
schema_version
created_at
git_commit
input_sha256
job_id
ansatz
depth
qubits
shots
seed
optimizer_method
maxiter
optimizer_success
optimizer_message
optimizer_evaluations
optimized_parameters
final_energy
energy_history
rank_count
node_count
qulacs_device
package_versions
wall_time_seconds
ranked_portfolios
```

Gunakan nama berdasarkan Slurm job ID supaya hasil tidak saling menimpa:

```text
notebooks/results/raw/vqe_results-<JOBID>.pkl
```

## 12. Isi file Slurm produksi

File `.job` adalah file yang dibaca `sbatch`. Semua baris `#SBATCH` harus berada di bagian atas, tepat setelah shebang dan sebelum command shell pertama.

### Aturan `#SBATCH`

| Directive | Isi |
| --- | --- |
| `#SBATCH -J` | Nama job, misalnya `deesc-hva` |
| `#SBATCH -p` | `Batch` |
| `#SBATCH -N` | Jumlah node |
| `#SBATCH -t` | Batas waktu job |
| `#SBATCH -o` | File standard output dengan `%j` |
| `#SBATCH -e` | File standard error dengan `%j` |

Jangan menambahkan `--account` atau `--qos` kalau Fujitsu tidak memberikannya.

Kalau memakai empat rank per node:

```text
total rank = 4 × jumlah node
```

mpiQulacs mewajibkan jumlah rank berupa pangkat dua. Jadi jumlah node yang aman untuk pola ini adalah:

```text
1, 2, 4, 8, 16, 32, ...
```

Contohnya:

| Node | Rank per node | Total rank | Valid |
| ---: | ---: | ---: | --- |
| 1 | 4 | 4 | Ya |
| 2 | 4 | 8 | Ya |
| 3 | 4 | 12 | Tidak |
| 4 | 4 | 16 | Ya |

### `sim-preflight.job`

File ini memakai jalur kode dan input 30 qubit yang sama dengan produksi, tapi optimizer dan sampling dibatasi. Ini bukan latihan; ini pengecekan wajib sebelum menghabiskan banyak waktu komputasi.

```bash
#!/bin/bash
#SBATCH -J deesc-check
#SBATCH -p Batch
#SBATCH -N 1
#SBATCH -t 00:30:00
#SBATCH -o logs/preflight-%j.out
#SBATCH -e logs/preflight-%j.err

set -euo pipefail
cd "$SLURM_SUBMIT_DIR"

PROJECT_DIR="$SLURM_SUBMIT_DIR"
QENV_DIR="$PROJECT_DIR/qenv"

test -x ./remote/job.sh
test -r ./remote/run_quantum.py
test -r ./notebooks/results/raw/qubo_ising_data.pkl
test -x "$QENV_DIR/bin/python"

export PYTHONUNBUFFERED=1

echo "job_id=$SLURM_JOB_ID"
echo "nodes=$SLURM_JOB_NUM_NODES"
echo "nodelist=$SLURM_JOB_NODELIST"

mpirun -npernode 4 \
  ./remote/job.sh \
  "$QENV_DIR" \
  "$QENV_DIR/bin/python" ./remote/run_quantum.py \
    --input notebooks/results/raw/qubo_ising_data.pkl \
    --output "notebooks/results/raw/preflight-${SLURM_JOB_ID}.pkl" \
    --ansatz hva \
    --depth 1 \
    --shots 16 \
    --seed 123 \
    --maxiter 2
```

### `sim-hva.job`

Ini baseline job produksi HVA:

```bash
#!/bin/bash
#SBATCH -J deesc-hva
#SBATCH -p Batch
#SBATCH -N 2
#SBATCH -t 08:00:00
#SBATCH -o logs/hva-%j.out
#SBATCH -e logs/hva-%j.err

set -euo pipefail
cd "$SLURM_SUBMIT_DIR"

PROJECT_DIR="$SLURM_SUBMIT_DIR"
QENV_DIR="$PROJECT_DIR/qenv"

test -x ./remote/job.sh
test -r ./remote/run_quantum.py
test -r ./notebooks/results/raw/qubo_ising_data.pkl
test -x "$QENV_DIR/bin/python"

export PYTHONUNBUFFERED=1

echo "job_id=$SLURM_JOB_ID"
echo "nodes=$SLURM_JOB_NUM_NODES"
echo "nodelist=$SLURM_JOB_NODELIST"

mpirun -npernode 4 \
  ./remote/job.sh \
  "$QENV_DIR" \
  "$QENV_DIR/bin/python" ./remote/run_quantum.py \
    --input notebooks/results/raw/qubo_ising_data.pkl \
    --output "notebooks/results/raw/vqe-hva-${SLURM_JOB_ID}.pkl" \
    --ansatz hva \
    --depth 2 \
    --shots 2000 \
    --seed 123 \
    --maxiter 300
```

Default HVA memakai 2 node karena circuit ZZ lebih berat. Setelah preflight dan HEA berhasil, bandingkan 1, 2, 4, dan 8 node hanya bila alokasi mengizinkan.

### `sim-hea.job`

Salin `sim-hva.job`, lalu ubah minimal bagian berikut:

```bash
#SBATCH -J deesc-hea
#SBATCH -N 1
#SBATCH -t 08:00:00
#SBATCH -o logs/hea-%j.out
#SBATCH -e logs/hea-%j.err
```

Dan argumen runner:

```bash
--output "notebooks/results/raw/vqe-hea-${SLURM_JOB_ID}.pkl" \
--ansatz hea
```

Jalankan HVA dan HEA sebagai job terpisah. HEA mempunyai lebih banyak parameter, tetapi circuit per evaluasinya lebih ringan daripada HVA.

### Yang tidak boleh ada di file `.job`

- password atau private key;
- `pip install` setiap kali job berjalan;
- plotting interaktif;
- Jupyter Notebook;
- command yang menulis hasil dari semua rank;
- partisi `IntrHPC` selama dinonaktifkan;
- `srun` sebagai pengganti `mpirun` tanpa instruksi terbaru dari Fujitsu.

## 13. Cek semua file sebelum submit

Panduan ini tidak membuat direktori baru. Pastikan direktori yang sudah menjadi bagian proyek tersedia sebelum `sbatch`, karena Slurm membuka file log sebelum menjalankan isi script:

```bash
cd ~/deescalation-vqe
test -d logs
test -d notebooks/results/raw
```

Cek file:

```bash
test -x remote/job.sh
test -r remote/run_quantum.py
test -r remote/sim-preflight.job
test -r remote/sim-hva.job
test -r remote/sim-hea.job
test -r notebooks/results/raw/qubo_ising_data.pkl
test -x qenv/bin/python
```

Cek sintaks shell:

```bash
bash -n remote/job.sh
bash -n remote/sim-preflight.job
bash -n remote/sim-hva.job
bash -n remote/sim-hea.job
```

Cek input dan commit:

```bash
sha256sum notebooks/results/raw/qubo_ising_data.pkl
git rev-parse HEAD
```

## 14. Step-by-step menjalankan preflight, HEA, dan HVA

Jalankan tahap berikut secara berurutan. Jangan submit HEA atau HVA sebelum preflight dinyatakan berhasil.

### Langkah 1 — masuk dan cek kesiapan

Masuk ke login server dan root proyek:

```bash
ssh qsim
cd ~/deescalation-vqe
```

Cek cluster, maintenance, environment, kode, dan input:

```bash
sinfo
sinfo -T
test -x qenv/bin/python
test -x remote/job.sh
test -r remote/run_quantum.py
test -r notebooks/results/raw/qubo_ising_data.pkl
bash -n remote/job.sh remote/sim-preflight.job remote/sim-hea.job remote/sim-hva.job
```

Semua command harus selesai tanpa pesan error. Jangan menguji import mpiQulacs pada login server karena environment dibuat untuk compute node A64FX; import package akan diuji oleh preflight di compute node.

### Langkah 2 — jalankan preflight kecil

```bash
sbatch remote/sim-preflight.job
```

Simpan angka yang ditampilkan Slurm:

```text
Submitted batch job <PREFLIGHT_JOBID>
```

Pantau sampai job tidak muncul lagi di antrean:

```bash
squeue -j <PREFLIGHT_JOBID>
sacct -j <PREFLIGHT_JOBID> \
  -o JobID,JobName%20,NNodes,AllocCPUS,Elapsed,State,ExitCode
```

Periksa log dan hasil:

```bash
cat logs/preflight-<PREFLIGHT_JOBID>.out
cat logs/preflight-<PREFLIGHT_JOBID>.err
test -r notebooks/results/raw/preflight-<PREFLIGHT_JOBID>.pkl
```

### Syarat preflight berhasil

Preflight dinyatakan **berhasil** hanya jika seluruh kondisi berikut terpenuhi:

- `sacct` menunjukkan `State=COMPLETED` dan `ExitCode=0:0`;
- file `logs/preflight-<JOBID>.err` kosong;
- log memuat `device = multi-cpu`;
- log memuat `optimizer selesai` dan `hasil disimpan`;
- `world_size` atau `rank_count` bernilai 4;
- hasil `preflight-<JOBID>.pkl` tersedia;
- hash input pada log/metadata sama dengan hash sebelum submit.

Periksa indikator utama dengan:

```bash
grep -E "device|native_zz|world_size|optimizer selesai|hasil disimpan|ERROR" \
  logs/preflight-<PREFLIGHT_JOBID>.out
wc -c logs/preflight-<PREFLIGHT_JOBID>.err
```

Nilai idealnya antara lain:

```text
world_size  = 4
device      = multi-cpu
native_zz   = True
```

`native_zz=False` tidak membuat preflight gagal karena runner mempunyai fallback. Namun HVA akan lebih berat; gunakan 4 node jika runtime 2 node diperkirakan tidak cukup.

Jika salah satu syarat gagal, **berhenti di tahap ini** dan perbaiki environment, path, MPI, atau error pada log.

### Langkah 3 — jalankan HEA

HEA dijalankan lebih dahulu karena circuit-nya lebih ringan dan hanya memakai 1 node:

```bash
sbatch remote/sim-hea.job
```

Simpan `<HEA_JOBID>`, lalu pantau dan periksa:

```bash
squeue -j <HEA_JOBID>
sacct -j <HEA_JOBID> \
  -o JobID,JobName%20,NNodes,AllocCPUS,Elapsed,State,ExitCode
tail -f logs/hea-<HEA_JOBID>.out
cat logs/hea-<HEA_JOBID>.err
test -r notebooks/results/raw/vqe-hea-<HEA_JOBID>.pkl
```

HEA berhasil jika statusnya `COMPLETED`, exit code `0:0`, stderr kosong, device `multi-cpu`, dan file hasil tersedia. Hentikan alur jika HEA gagal; jangan langsung menambah node sebelum membaca error.

### Langkah 4 — jalankan HVA

Setelah preflight dan HEA berhasil, jalankan HVA default dengan 2 node:

```bash
sbatch remote/sim-hva.job
```

Simpan `<HVA_JOBID>`, lalu pantau dan periksa:

```bash
squeue -j <HVA_JOBID>
sacct -j <HVA_JOBID> \
  -o JobID,JobName%20,NNodes,AllocCPUS,Elapsed,State,ExitCode
tail -f logs/hva-<HVA_JOBID>.out
cat logs/hva-<HVA_JOBID>.err
test -r notebooks/results/raw/vqe-hva-<HVA_JOBID>.pkl
```

HVA berhasil dengan kriteria yang sama: `COMPLETED`, exit code `0:0`, stderr kosong, device `multi-cpu`, optimizer selesai, dan file hasil tersedia.

Jika preflight melaporkan `native_zz=False`, konfigurasi HVA yang lebih aman adalah:

```bash
sbatch -N 4 -t 12:00:00 remote/sim-hva.job
```

Urutan akhirnya adalah:

```text
cek kesiapan → preflight → validasi preflight → HEA → validasi HEA → HVA → validasi HVA
```

## 15. Pantau job

Lihat job milik sendiri:

```bash
squeue
```

Lihat penggunaan node semua pengguna melalui command khusus Fujitsu:

```bash
squeues
```

`squeues` bukan command Slurm standar, tapi memang tersedia di sistem Fujitsu.

Lihat detail satu job:

```bash
scontrol show job <JOBID>
```

Pantau log:

```bash
tail -f logs/hva-<JOBID>.out
tail -f logs/hva-<JOBID>.err
```

Batalkan job:

```bash
scancel <JOBID>
```

Cek hasil accounting:

```bash
sacct -j <JOBID> \
  -o JobID,JobName%20,Partition,NNodes,AllocCPUS,Start,End,Elapsed,State,ExitCode
```

Status yang sering muncul:

| Status | Arti |
| --- | --- |
| `PD` | Masih menunggu resource |
| `R` | Sedang berjalan |
| `CD` | Selesai |
| `F` | Gagal |
| `TO` | Melewati batas waktu |
| `NF` | Gagal karena node |
| `CA` | Dibatalkan |

## 16. Ambil hasil ke lokal

Setelah job berstatus `COMPLETED`, jalankan dari komputer lokal:

```bash
cd /home/quantoqi/Documents/Fujistsu/De-escalation_War
PREFLIGHT_JOBID=123456  # ganti dengan job ID preflight
HEA_JOBID=123457        # ganti dengan job ID HEA
HVA_JOBID=123458        # ganti dengan job ID HVA

rsync -av --progress \
  qsim:~/deescalation-vqe/notebooks/results/raw/preflight-${PREFLIGHT_JOBID}.pkl \
  notebooks/results/raw/

rsync -av --progress \
  qsim:~/deescalation-vqe/notebooks/results/raw/vqe-hea-${HEA_JOBID}.pkl \
  notebooks/results/raw/

rsync -av --progress \
  qsim:~/deescalation-vqe/notebooks/results/raw/vqe-hva-${HVA_JOBID}.pkl \
  notebooks/results/raw/

rsync -av --progress \
  qsim:~/deescalation-vqe/logs/ \
  logs/
```

Cek metadata hasil:

- job ID benar;
- input hash benar;
- ansatz dan depth benar;
- optimizer selesai;
- jumlah rank dan node benar;
- device tercatat sebagai `multi-cpu`;
- log error kosong atau sudah dipahami.

Kalau hasil sudah dipilih, buat nama yang dipakai notebook lokal:

```bash
cp "notebooks/results/raw/vqe-hva-${HVA_JOBID}.pkl" \
  notebooks/results/raw/vqe_results.pkl
```

Lalu jalankan evaluasi lokal:

```bash
PYTHONPATH="$PWD" jupyter nbconvert --to notebook --execute \
  notebooks/04_compare_baseline.ipynb \
  --output 04_compare_baseline.executed.ipynb
```

Jangan membuka pickle dari sumber yang tidak dipercaya. File pickle bisa menjalankan kode saat dibaca.

## 17. Total resource yang digunakan

Perkiraan minimum memori state vector:

```text
memori = 2^jumlah_qubit × 16 byte
```

| Qubit | Memori state vector |
| ---: | ---: |
| 20 | 16 MiB |
| 25 | 512 MiB |
| 30 | 16 GiB |
| 35 | 512 GiB |
| 40 | 16 TiB |

Angka tersebut belum menghitung circuit, observable, buffer MPI, temporary state, NumPy, SciPy, dan optimizer. Setiap node A64FX mempunyai sekitar 32 GiB memori dan 48 compute core.

### Resource setiap tahap

Konfigurasi job yang digunakan dalam proyek:

| Tahap | Node | Rank/node | Total rank | Thread/rank | Total core | State/rank | State/node | Batas waktu | Maksimum node-hour |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Setup `qenv` pertama kali | 1 | – | – | – | 48 tersedia | – | – | 2 jam | 2 |
| Preflight | 1 | 4 | 4 | 12 | 48 | 4 GiB | 16 GiB | 30 menit | 0,5 |
| HEA depth 2 | 1 | 4 | 4 | 12 | 48 | 4 GiB | 16 GiB | 8 jam | 8 |
| HVA depth 2 | 2 | 4 | 8 | 12 | 96 | 2 GiB | 8 GiB | 8 jam | 16 |

Untuk eksekusi pertama, jika semua tahap memakai seluruh batas waktunya:

```text
total node-hour = setup qenv + preflight + HEA + HVA
                = (1 × 2) + (1 × 0,5) + (1 × 8) + (2 × 8)
                = 26,5 node-hour
```

Untuk eksperimen berikutnya, `qenv` tidak dibuat ulang sehingga total maksimum menjadi 24,5 node-hour.

`Node-hour` bukan durasi yang dilihat pengguna. Contohnya, HVA berjalan maksimal 8 jam, tetapi memakai 2 node sehingga biayanya maksimal 16 node-hour.

### Arti penggunaan CPU

Wrapper membagi 48 core pada satu node seperti berikut:

```text
mpiQulacs memakai `OMP_NUM_THREADS=1` dan `QULACS_NUM_THREADS=48`, sesuai
contoh resmi Fujitsu Quantum Simulator2.
```

Konfigurasi ini harus dipertahankan kecuali Fujitsu memberikan wrapper resmi
yang berbeda. Jangan membagi `QULACS_NUM_THREADS` berdasarkan jumlah rank.

### Beban circuit

Untuk input 30 qubit saat ini:

| Ansatz | Parameter | Gate per evaluasi | Observable term | Catatan |
| --- | ---: | ---: | ---: | --- |
| Preflight HVA depth 1 | 2 | 525 | 495 | Hanya 2 evaluasi dan 16 shots |
| HEA depth 2 | 150 | 210 | 495 | Circuit ringan, parameter banyak |
| HVA depth 2 native ZZ | 4 | 1.020 | 495 | Memakai satu PauliRotation per coupling ZZ |
| HVA depth 2 fallback | 4 | 2.760 | 495 | Dipakai otomatis bila native ZZ tidak tersedia |

Resource aktual dan jumlah gate yang benar-benar dipakai dicetak pada log dan disimpan dalam metadata `resource_estimate`.

### Cara melihat resource yang sedang digunakan

Saat job menunggu atau berjalan:

```bash
squeue -j <JOBID> -o "%.18i %.12j %.2t %.10M %.6D %.6C %R"
scontrol show job <JOBID>
```

Setelah job selesai:

```bash
sacct -j <JOBID> \
  -o JobID,JobName%20,NNodes,AllocCPUS,Elapsed,State,ExitCode
```

Kolom penting:

- `NNodes`: jumlah komputer/node yang diberikan;
- `AllocCPUS`: total core yang dialokasikan;
- `Elapsed`: waktu yang benar-benar digunakan;
- `State`: status akhir;
- `ExitCode`: `0:0` berarti program selesai normal.

Hitung pemakaian aktual secara sederhana:

```text
node-hour aktual = jumlah node × elapsed dalam jam
```

Contoh: HVA selesai dalam 3 jam pada 2 node berarti memakai sekitar 6 node-hour, bukan maksimum 16 node-hour.

### Kapan menambah node

Jangan langsung meminta node sebanyak mungkin. Komunikasi MPI juga mempunyai biaya. Tambah HVA dari 2 menjadi 4 node hanya jika:

- preflight dan HVA 2-node sudah berjalan benar;
- HVA mendekati batas waktu;
- `native_zz=False`; atau
- benchmark menunjukkan wall time turun secara berarti.

Jumlah node yang aman untuk pola 4 rank/node adalah 1, 2, 4, 8, dan seterusnya agar total rank tetap berupa pangkat dua.

## 18. Masalah yang sering muncul

### SSH tidak bisa dibuka

Cek:

- permission `/etc/ssh`;
- permission `~/.ssh/config`;
- static global IP;
- port Fujitsu;
- private key yang dipakai;
- konfigurasi `qsim-gw` dan `qsim`.

Kalau host key berubah:

```bash
ssh-keygen -R 125.206.100.37
ssh-keygen -R login-server
ssh qsim
```

Jangan menghapus seluruh `known_hosts`.

### Segmentation fault

Pastikan runner punya:

```python
from mpi4py import MPI
```

Cek juga:

- environment memakai `mpiQulacs`, bukan `qulacs` biasa;
- jumlah rank adalah pangkat dua;
- semua rank menjalankan urutan simulator yang sama.

### `cannot allocate memory in static TLS block`

Pastikan `job.sh` memuat:

```bash
export LD_PRELOAD=/lib64/libgomp.so.1
```

Jangan memakai `libgomp.so` dari lokasi lain.

### Job terus `PENDING`

Cek:

```bash
sinfo
sinfo -T
squeue
squeues
```

Kemungkinan penyebab:

- node belum tersedia;
- jumlah node terlalu besar;
- time limit bertabrakan dengan maintenance;
- partisi salah.

### Output muncul berkali-kali

Semua rank menjalankan program yang sama. Batasi print ke rank 0:

```python
if rank == 0:
    print(message)
```

### Job hang atau hasil antar-rank berbeda

Cek:

- seed sama pada semua rank;
- circuit sama pada semua rank;
- sampling dipanggil semua rank;
- optimizer berjalan di semua rank;
- tidak ada operasi MPI di dalam blok khusus rank 0;
- `OMP_NUM_THREADS=1` dan `QULACS_NUM_THREADS=48` sesuai wrapper resmi;

### Job selesai tapi device masih `cpu`

Cek:

- semua state memakai `use_multi_cpu=True`;
- jumlah rank yang benar-benar berjalan;
- jumlah qubit;
- output `state.get_device_name()`.

`use_multi_cpu=True` tidak selalu berarti state pasti dibagi untuk semua ukuran circuit dan konfigurasi rank.

## 19. Checklist sebelum produksi

### Koneksi

- [ ] Static global IP sudah didaftarkan.
- [ ] `ssh -G qsim` tidak error.
- [ ] `ssh qsim` masuk ke `loginvm-XXX`.
- [ ] `salloc` bisa memberikan compute node `fx-XX-XX-XX`.

### Kode dan data

- [ ] Bug HVA sudah berubah dari `beta` ke `gamma`.
- [ ] Semua state remote memakai `use_multi_cpu=True`.
- [ ] Runner mengimpor MPI.
- [ ] Semua rank menjalankan operasi simulator yang sama.
- [ ] Hanya rank 0 yang menulis output.
- [ ] Sampling memakai seed.
- [ ] `qubo_ising_data.pkl` tersedia.
- [ ] Hash input lokal dan remote sama.

### Environment

- [ ] `qenv` dibuat dari compute node.
- [ ] `mpi4py`, NumPy, SciPy, dan mpiQulacs bisa diimpor.
- [ ] `qulacs` biasa tidak terinstal bersama mpiQulacs.
- [ ] Versi package sudah dicatat.

### File Slurm

- [ ] `remote/job.sh` executable.
- [ ] `remote/run_quantum.py` tersedia.
- [ ] `remote/sim-preflight.job` tersedia.
- [ ] `remote/sim-hva.job` tersedia.
- [ ] `remote/sim-hea.job` tersedia.
- [ ] Semua file shell lolos `bash -n`.
- [ ] Partisi yang dipakai adalah `Batch`.
- [ ] Total rank adalah pangkat dua.
- [ ] Folder `notebooks/results/raw` dan `logs` sudah ada.

### Setelah job

- [ ] Status `sacct` adalah `COMPLETED`.
- [ ] Exit code sudah dicek.
- [ ] Standard error sudah dicek.
- [ ] Hasil berdasarkan job ID sudah diambil ke lokal.
- [ ] Metadata hasil sudah diperiksa.
- [ ] Hasil terpilih sudah disalin menjadi `vqe_results.pkl`.
- [ ] Notebook evaluasi lokal berhasil dijalankan.

## 20. Bagian dokumen resmi yang dipakai

| Topik | Bagian PDF Fujitsu |
| --- | --- |
| Susunan server dan spesifikasi node | 1.1 System Configuration |
| Slurm dan aturan partisi QSC | 1.2 Job Scheduler |
| SSH dan transfer file | 2. Login |
| Setup venv dan mpiQulacs | 3. Job Execution Method |
| Command Slurm | 4. Slurm Command |
| Python dan aturan MPI | 6. Python |
| VQE multi-node | 9. Sample Code |
| Segmentation fault dan `LD_PRELOAD` | 10. Troubleshooting |
| API dan batasan mpiQulacs | mpiQulacs: Usage, Important Notes, Limitations |

Kalau dokumentasi baru dari Fujitsu berbeda dengan panduan ini, ikuti dokumentasi terbaru dan perbarui file ini.
