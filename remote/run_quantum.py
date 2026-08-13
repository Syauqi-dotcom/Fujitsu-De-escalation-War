#!/usr/bin/env python3

import argparse
import hashlib
import os
import pickle
import subprocess
import sys
import time
from datetime import datetime, timezone

import numpy as np

from mpi4py import MPI

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
world_size = comm.Get_size()

from qulacs import Observable, QuantumCircuit, QuantumState
from scipy.optimize import minimize

HAS_NATIVE_ZZ_ROTATION = hasattr(
    QuantumCircuit, "add_multi_Pauli_rotation_gate"
)

# Import helper dari src/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.qubo import qubo_value


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        ).decode().strip()
    except Exception:
        return "unknown"


def _package_versions() -> dict:
    import importlib
    pkgs = ["mpi4py", "numpy", "scipy", "qulacs"]
    out = {}
    for p in pkgs:
        try:
            mod = importlib.import_module(p)
            out[p] = getattr(mod, "__version__", "?")
        except ImportError:
            out[p] = "not installed"
    return out


def _validate_input(data: dict, expected_qubits: int):
    required_keys = {"K", "g", "q", "Q", "const"}
    missing = required_keys - data.keys()
    if missing:
        raise ValueError(f"Key yang hilang di input: {missing}")

    K = np.asarray(data["K"])
    g = np.asarray(data["g"])
    q = np.asarray(data["q"])
    Q = np.asarray(data["Q"])

    if K.ndim != 2 or K.shape[0] != K.shape[1]:
        raise ValueError(f"K harus matriks persegi; dapat shape {K.shape}")

    if g.ndim != 1 or Q.ndim != 2 or q.ndim != 1:
        raise ValueError("g harus 1D, Q harus 2D, q harus 1D")
        
    m = K.shape[0]
    if g.shape[0] != m or q.shape[0] != m or Q.shape != (m, m):
        raise ValueError(f"Dimensi tidak konsisten: K={K.shape}, g={g.shape}, Q={Q.shape}, q={q.shape}")
    if not (
        np.isfinite(K).all()
        and np.isfinite(g).all()
        and np.isfinite(q).all()
        and np.isfinite(Q).all()
        and np.isfinite(data["const"])
    ):
        raise ValueError("K, g, q, Q, atau const mengandung NaN/infinity")
    if m != expected_qubits:
        raise ValueError(
            f"Jumlah qubit di data ({m}) tidak sama dengan --qubits ({expected_qubits})"
        )


# ════════════════════════════════════════════════════════════════════════════
# Circuit builder
# ════════════════════════════════════════════════════════════════════════════

def build_observable(K, g, gamma_tf=0.2):
    m = len(g)
    obs = Observable(m)
    for k in range(m):
        if abs(g[k]) > 1e-14:
            obs.add_operator(float(g[k]), f"Z {k}")
    for k in range(m):
        for ell in range(k + 1, m):
            if abs(K[k, ell]) > 1e-14:
                obs.add_operator(float(K[k, ell]), f"Z {k} Z {ell}")
    if abs(gamma_tf) > 1e-14:
        for k in range(m):
            obs.add_operator(float(-gamma_tf), f"X {k}")
    return obs


def build_hva_circuit(K, g, params):
    m = len(g)
    p = len(params) // 2
    gammas = params[:p]
    betas = params[p:]
    
    circuit = QuantumCircuit(m)
    for k in range(m):
        circuit.add_H_gate(k)
    for r in range(p):
        gamma = gammas[r]
        beta = betas[r]
        for k in range(m):
            angle = 2.0 * gamma * g[k]
            if abs(angle) > 1e-14:
                circuit.add_RZ_gate(k, angle)
        for k in range(m):
            for ell in range(k + 1, m):
                angle = 2.0 * gamma * K[k, ell]
                if abs(angle) > 1e-14:
                    if HAS_NATIVE_ZZ_ROTATION:
                        circuit.add_multi_Pauli_rotation_gate(
                            [k, ell], [3, 3], angle
                        )
                    else:
                        circuit.add_CNOT_gate(k, ell)
                        circuit.add_RZ_gate(ell, angle)
                        circuit.add_CNOT_gate(k, ell)
        for k in range(m):
            circuit.add_RX_gate(k, 2.0 * beta)
    return circuit


def build_hea_circuit(m, params, depth):
    circuit = QuantumCircuit(m)
    idx = 0
    for k in range(m):
        circuit.add_RY_gate(k, params[idx])
        idx += 1
    for _ in range(depth):
        for k in range(m):
            circuit.add_RY_gate(k, params[idx]); idx += 1
            circuit.add_RZ_gate(k, params[idx]); idx += 1
        for k in range(m - 1):
            circuit.add_CNOT_gate(k, k + 1)
        circuit.add_CNOT_gate(m - 1, 0)
    return circuit


def evaluate_energy_hva(params, K, g, observable, state):
    """Evaluasi HVA dengan memakai ulang state terdistribusi yang sama."""
    state.set_zero_state()
    circuit = build_hva_circuit(K, g, params)
    circuit.update_quantum_state(state)
    return observable.get_expectation_value(state).real


def evaluate_energy_hea(params, m, depth, observable, state):
    """Evaluasi HEA dengan memakai ulang state terdistribusi yang sama."""
    state.set_zero_state()
    circuit = build_hea_circuit(m, params, depth)
    circuit.update_quantum_state(state)
    return observable.get_expectation_value(state).real


def _decode_samples(raw_samples, m):
    """Dekode integer sample secara vektor tanpa loop Python per bit."""
    encoded = np.asarray(raw_samples, dtype=np.uint64)[:, None]
    bit_positions = np.arange(m, dtype=np.uint64)[None, :]
    return ((encoded >> bit_positions) & 1).astype(np.int8)


def sample_hva(K, g, params, n_shots, seed, state):
    m = len(g)
    state.set_zero_state()
    circuit = build_hva_circuit(K, g, params)
    circuit.update_quantum_state(state)
    raw = state.sampling(n_shots, seed)            
    return _decode_samples(raw, m)


def sample_hea(m, params, depth, n_shots, seed, state):
    state.set_zero_state()
    circuit = build_hea_circuit(m, params, depth)
    circuit.update_quantum_state(state)
    raw = state.sampling(n_shots, seed)          
    return _decode_samples(raw, m)


def rank_portfolios(samples, q, Q, const, top_k=20):
    unique = {}
    for x in samples:
        key = tuple(int(v) for v in x)
        if key not in unique:
            unique[key] = qubo_value(x, q, Q, const)
    ranked = sorted(unique.items(), key=lambda kv: kv[1])
    return ranked[:top_k]


def estimate_problem_resources(K, g, gamma_tf, ansatz, depth, rank_count):
    """Hitung ukuran problem aktual untuk metadata dan perencanaan resource."""
    m = len(g)
    nonzero_fields = int(np.count_nonzero(np.abs(g) > 1e-14))
    nonzero_couplings = int(
        np.count_nonzero(np.abs(np.triu(K, k=1)) > 1e-14)
    )
    transverse_terms = m if abs(gamma_tf) > 1e-14 else 0
    observable_terms = nonzero_fields + nonzero_couplings + transverse_terms

    if ansatz == "hva":
        parameter_count = 2 * depth
        gates_per_coupling = 1 if HAS_NATIVE_ZZ_ROTATION else 3
        circuit_gates = m + depth * (
            nonzero_fields
            + gates_per_coupling * nonzero_couplings
            + m
        )
    else:
        parameter_count = m + 2 * m * depth
        circuit_gates = m + 3 * m * depth

    global_state_bytes = (1 << m) * np.dtype(np.complex128).itemsize
    return {
        "parameter_count": parameter_count,
        "circuit_gate_count": circuit_gates,
        "observable_term_count": observable_terms,
        "nonzero_field_count": nonzero_fields,
        "nonzero_coupling_count": nonzero_couplings,
        "native_zz_rotation": HAS_NATIVE_ZZ_ROTATION,
        "global_state_bytes": global_state_bytes,
        "state_bytes_per_rank": global_state_bytes // rank_count,
    }


# ════════════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════════════

def parse_args():
    p = argparse.ArgumentParser(
        description="VQE runner untuk Fujitsu Quantum Simulator2 (MPI-aware)"
    )
    p.add_argument("--input",   required=True, help="Path input pickle (qubo_ising_data.pkl)")
    p.add_argument("--output",  required=True, help="Path output pickle (vqe_results-<JOBID>.pkl)")
    p.add_argument("--ansatz",  required=True, choices=["hva", "hea"])
    p.add_argument("--depth",   type=int, required=True)
    p.add_argument("--shots",   type=int, required=True)
    p.add_argument("--seed",    type=int, required=True)
    p.add_argument("--maxiter", type=int, required=True)
    p.add_argument("--qubits",  type=int, default=30)
    p.add_argument("--gamma-tf", type=float, default=0.2)
    return p.parse_args()


def main():
    args = parse_args()
    t_start = time.time()

    if args.depth <= 0:
        raise ValueError("--depth harus positif")
    if args.shots <= 0:
        raise ValueError("--shots harus positif")
    if args.maxiter <= 0:
        raise ValueError("--maxiter harus positif")
    if args.qubits <= 0:
        raise ValueError("--qubits harus positif")
        
    if os.path.abspath(args.input) == os.path.abspath(args.output):
        raise ValueError("--input dan --output tidak boleh sama")
    output_parent = os.path.dirname(os.path.abspath(args.output))
    if not os.path.isdir(output_parent):
        raise FileNotFoundError(
            f"Direktori output harus sudah ada: {output_parent}"
        )

    input_sha = _sha256(args.input)
    with open(args.input, "rb") as f:
        data = pickle.load(f)

    _validate_input(data, args.qubits)

    K = np.asarray(data["K"])
    g = np.asarray(data["g"])
    q = np.asarray(data["q"])
    Q = np.asarray(data["Q"])
    const = float(data["const"])
    m = len(g)

    if world_size > 1 and (world_size & (world_size - 1)) != 0:
        raise ValueError(
            f"Jumlah rank ({world_size}) harus pangkat dua (persyaratan mpiQulacs)"
        )

    if rank == 0:
        print(f"[rank 0] job_id      = {os.environ.get('SLURM_JOB_ID', 'local')}")
        print(f"[rank 0] ansatz      = {args.ansatz}")
        print(f"[rank 0] qubits      = {m}")
        print(f"[rank 0] depth       = {args.depth}")
        print(f"[rank 0] shots       = {args.shots}")
        print(f"[rank 0] seed        = {args.seed}")
        print(f"[rank 0] maxiter     = {args.maxiter}")
        print(f"[rank 0] world_size  = {world_size}")
        print(f"[rank 0] input_sha   = {input_sha}")
        sys.stdout.flush()

    observable = build_observable(K, g, gamma_tf=args.gamma_tf)

    state = QuantumState(m, use_multi_cpu=True)
    qulacs_device = state.get_device_name()
    if world_size > 1 and "multi" not in qulacs_device.lower():
        raise RuntimeError(
            f"mpiQulacs tidak aktif: device='{qulacs_device}', expected multi-cpu"
        )

    resource_estimate = estimate_problem_resources(
        K, g, args.gamma_tf, args.ansatz, args.depth, world_size
    )

    if rank == 0:
        print(f"[rank 0] device      = {qulacs_device}")
        print(f"[rank 0] parameters  = {resource_estimate['parameter_count']}")
        print(f"[rank 0] gates/eval  = {resource_estimate['circuit_gate_count']}")
        print(f"[rank 0] terms/eval  = {resource_estimate['observable_term_count']}")
        print(f"[rank 0] native_zz   = {resource_estimate['native_zz_rotation']}")
        sys.stdout.flush()

    rng = np.random.default_rng(args.seed)
    energy_history = []

    if args.ansatz == "hva":
        x0 = rng.uniform(low=-0.1, high=0.1, size=2 * args.depth)

        def objective(params):
            e = evaluate_energy_hva(params, K, g, observable, state)
            energy_history.append(float(e))
            if rank == 0 and len(energy_history) % 50 == 0:
                print(f"[rank 0] iter {len(energy_history):4d}  energy={e:.6f}")
                sys.stdout.flush()
            return e

    else:  # hea
        num_params = m + 2 * m * args.depth
        x0 = rng.uniform(low=-np.pi, high=np.pi, size=num_params)

        def objective(params):
            e = evaluate_energy_hea(params, m, args.depth, observable, state)
            energy_history.append(float(e))
            if rank == 0 and len(energy_history) % 50 == 0:
                print(f"[rank 0] iter {len(energy_history):4d}  energy={e:.6f}")
                sys.stdout.flush()
            return e

    res = minimize(
        objective,
        x0,
        method="COBYLA",
        options={"maxiter": args.maxiter, "rhobeg": 0.5, "tol": 1e-4},
    )

    if rank == 0:
        print(f"[rank 0] optimizer selesai: success={res.success} msg='{res.message}'")
        sys.stdout.flush()

    if args.ansatz == "hva":
        samples = sample_hva(K, g, res.x, args.shots, args.seed, state)
    else:
        samples = sample_hea(m, res.x, args.depth, args.shots, args.seed, state)

    if rank == 0:
        ranked = rank_portfolios(samples, q, Q, const, top_k=20)

        result = {
            "schema_version":       2,
            "created_at":           datetime.now(timezone.utc).isoformat(),
            "git_commit":           _git_commit(),
            "input_sha256":         input_sha,
            "job_id":               os.environ.get("SLURM_JOB_ID", "local"),
            "ansatz":               args.ansatz,
            "depth":                args.depth,
            "qubits":               m,
            "gamma_tf":             args.gamma_tf,
            "shots":                args.shots,
            "seed":                 args.seed,
            "optimizer_method":     "COBYLA",
            "maxiter":              args.maxiter,
            "optimizer_success":    bool(res.success),
            "optimizer_message":    str(res.message),
            "optimizer_evaluations": int(getattr(res, "nfev", len(energy_history))),
            "optimized_parameters": res.x.tolist(),
            "final_energy":         float(res.fun),
            "energy_history":       energy_history,
            "rank_count":           world_size,
            "node_count":           int(os.environ.get("SLURM_JOB_NUM_NODES", 1)),
            "qulacs_device":        qulacs_device,
            "qulacs_threads_per_rank": int(os.environ.get("QULACS_NUM_THREADS", 1)),
            "resource_estimate":    resource_estimate,
            "package_versions":     _package_versions(),
            "wall_time_seconds":    time.time() - t_start,
            "ranked_portfolios":    ranked,
        }

        with open(args.output, "wb") as f:
            pickle.dump(result, f, protocol=4)

        print(f"[rank 0] hasil disimpan: {args.output}")
        print(f"[rank 0] wall_time      = {result['wall_time_seconds']:.1f}s")
        print(f"[rank 0] qulacs_device  = {qulacs_device}")
        sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[rank {rank}] ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
