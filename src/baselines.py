from .qubo import qubo_value
import numpy as np


def _flip_delta(x, q, Q, bit_index):
    field = float(q[bit_index])
    for other_index in range(len(x)):
        if other_index == bit_index:
            continue
        row, column = sorted((bit_index, other_index))
        field += Q[row, column] * x[other_index]
    return (1 - 2 * x[bit_index]) * field


def local_search(x, q, Q, max_sweeps=100):
    x = x.copy().astype(int)
    m = len(x)
    for _ in range(max_sweeps):
        improved = False
        for k in range(m):
            delta = _flip_delta(x, q, Q, k)
            if delta < -1e-12:
                x[k] = 1 - x[k]
                improved = True
        if not improved:
            break
    return x


def simulated_annealing(
    q, Q, const=0.0, n_steps=20000, t0=1.0, tf=1e-3, seed=123
):
    if n_steps <= 0:
        raise ValueError("n_steps harus positif")
    if t0 <= 0.0 or tf <= 0.0:
        raise ValueError("t0 dan tf harus positif")

    rng = np.random.default_rng(seed)
    m = len(q)
    x = rng.integers(0, 2, size=m)
    fx = qubo_value(x, q, Q, const)
    best_x = x.copy()
    best_fx = fx

    for step in range(n_steps):
        frac = step / max(1, n_steps - 1)
        temp = t0 * (tf / t0) ** frac
        k = rng.integers(0, m)
        delta = _flip_delta(x, q, Q, k)
        if delta < 0 or rng.random() < np.exp(-delta / max(temp, 1e-12)):
            x[k] = 1 - x[k]
            fx += delta
            if fx < best_fx:
                best_x, best_fx = x.copy(), fx

    # Hitung ulang satu kali agar nilai keluaran tidak menyimpan drift floating
    # point dari ribuan pembaruan inkremental.
    return best_x, qubo_value(best_x, q, Q, const)
