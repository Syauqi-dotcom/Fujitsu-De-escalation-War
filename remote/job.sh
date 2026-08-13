#!/usr/bin/env bash
# remote/job.sh
# Wrapper yang dipanggil mpirun di setiap rank untuk menyiapkan environment.
# Argumen: <path-venv> <command> [args...]
# Lihat §10 HOW_TO_REMOTE_AND_MIGRATE.md untuk penjelasan lengkap.
set -euo pipefail

# ── Thread dan binding ───────────────────────────────────────────────────────
export UCX_IB_MLX5_DEVX=no
export OMP_PROC_BIND=TRUE

# Ikuti konfigurasi job.sh contoh resmi Fujitsu Quantum Simulator2:
# OpenMP dipaksa satu thread, sedangkan mpiQulacs mengelola 48 thread A64FX.
# Jangan membagi QULACS_NUM_THREADS menjadi 48/local_size.
local_size=${OMPI_COMM_WORLD_LOCAL_SIZE:?OMPI_COMM_WORLD_LOCAL_SIZE tidak tersedia}
local_rank=${OMPI_COMM_WORLD_LOCAL_RANK:?OMPI_COMM_WORLD_LOCAL_RANK tidak tersedia}
export OMP_NUM_THREADS=1
export QULACS_NUM_THREADS=48

# ── Aktifkan venv ────────────────────────────────────────────────────────────
source "$1/bin/activate"
shift

# ── libgomp workaround (Fujitsu official) ───────────────────────────────────
if [ -z "${LD_PRELOAD:-}" ]; then
    export LD_PRELOAD=/lib64/libgomp.so.1
else
    export LD_PRELOAD=/lib64/libgomp.so.1:"$LD_PRELOAD"
fi

# ── NUMA binding ─────────────────────────────────────────────────────────────
command_name=$1
shift

if [ "$local_size" -eq 1 ]; then
    numactl -m 0-3 -N 0-3 "$command_name" "$@"
elif [ "$local_size" -eq 4 ]; then
    numactl -N "$local_rank" -m "$local_rank" "$command_name" "$@"
else
    "$command_name" "$@"
fi
