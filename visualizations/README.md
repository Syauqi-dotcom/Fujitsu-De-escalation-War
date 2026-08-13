# Visualisasi circuit VQE

File utama: [`vqe_circuit_visualization.svg`](./vqe_circuit_visualization.svg).
Figur menggunakan gaya monokrom seperti diagram pada paper: latar putih,
tipografi serif, garis circuit hitam, panel `(a)`/`(b)`, dan tanpa elemen
dekoratif berwarna.

Diagram ini diturunkan langsung dari `build_hva_circuit()` dan
`build_hea_circuit()` di `src/qulacs_vqe.py`, dengan konfigurasi produksi pada
`remote/sim-hva.job` dan `remote/sim-hea.job`:

- 30 qubit;
- depth `p = 2`;
- 2.000 shots;
- HVA memakai 4 parameter bersama: `gamma_1`, `gamma_2`, `beta_1`, `beta_2`;
- HEA memakai `m + 2mp = 150` parameter independen.

## Cara membaca HVA

1. Semua qubit dimulai dari `|0>` dan diberi gate H.
2. Untuk setiap lapis `r`, local field Ising direalisasikan sebagai
   `RZ(2 gamma_r g_k)`.
3. Setiap coupling nonzero `K[k,l]` direalisasikan sebagai
   `CNOT(k,l) -> RZ_l(2 gamma_r K[k,l]) -> CNOT(k,l)`.
4. Semua qubit diberi mixer `RX(2 beta_r)`.
5. Blok langkah 2–4 diulang dua kali, lalu state disampling.

Karena penalti budget menambahkan coupling pasangan aksi, instance 30-qubit
dapat memiliki seluruh `30 choose 2 = 435` blok ZZ per lapis. Implementasi
mengeksekusinya berurutan menurut loop `k < l`; kotak ZZ pada diagram adalah
representasi pola tersebut, bukan hanya dua coupling yang digambar.

`gamma_tf = 0.2` masuk ke observable energi sebagai transverse field `-gamma_tf
sum X_k`. Nilai itu tidak menjadi gate tersendiri di ansatz HVA.

## Cara membaca HEA

1. Setiap qubit mendapat rotasi awal `RY` dengan parameter sendiri.
2. Setiap lapis memberi `RY` lalu `RZ` pada setiap qubit.
3. CNOT menghubungkan `q0 -> q1 -> ... -> q29`, kemudian `q29 -> q0` untuk
   menutup ring.
4. Blok rotasi dan ring diulang dua kali, lalu state disampling.

SVG dipilih agar teks dan garis circuit tetap tajam ketika diperbesar atau
dimasukkan ke laporan/presentasi.

Versi PNG siap pakai tersedia di
[`vqe_circuit_visualization.png`](./vqe_circuit_visualization.png). PNG dapat
dibuat ulang dari SVG dengan:

```bash
google-chrome --headless=new --no-sandbox --disable-gpu --hide-scrollbars \
  --force-device-scale-factor=1 --window-size=1800,1250 \
  --screenshot=visualizations/vqe_circuit_visualization.png \
  file://"$PWD"/visualizations/vqe_circuit_visualization.svg
```
