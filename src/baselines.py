from .qubo import qubo_value
import numpy as np

def local_search(x, q, Q, max_sweeps=100):
    x = x.copy().astype(int)
    m = len(x)
    for _ in range(max_sweeps):
        improved = False
        for k in range(m):
            field = q[k]
            for ell in range(m):
                if ell == k:
                    continue
                a, b = min(k, ell), max(k, ell)
                field += Q[a,b] * x[ell]
            delta = (1-2 * x[k]) * field
            if delta < -1e-12:
                x[k] = 1 - x[k]
                improved = True 
        if not improved:
            break 
    return x

def simmulated_annealing(q, Q, const=0.0, n_steps=20000, t0=1.0, tf=1e-3, seed=123):
    rng = np.random.default_rng(seed)
    m = len(q)
    x = rng.integers(0, 2, size=m)
    fx = qubo_value(x, q, Q, const)
    best_x = x.copy()
    best_fx = fx

    for step in range(n_steps):
        frac = step /max(1, n_steps -1)
        temp = t0 * (tf / t0) ** frac
        k = rng.integers(0, m)
        x_new = x.copy()
        x_new[k] = 1 - x_new[k]
        f_new = qubo_value(x_new, q, Q, const)
        delta = f_new - fx 
        if delta < 0  or rng.random() < np.exp(-delta / max (temp, 1e-12)):
            x, fx = x_new, f_new
            if fx < best_fx:
                best_x, best_fx = x.copy(), fx 
    return best_x, best_fx


