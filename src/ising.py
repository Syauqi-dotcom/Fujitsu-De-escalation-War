import numpy as np 

def qubo_to_ising(q, Q, const = 0.0):
    m = len(q)
    K = np.zeros((m,m), dtype = float)
    g = np.zeros(m, dtype=float)
    c = const + 0.5 * np.sum(q)

    for k in range(m):
        g[k] += -0.5 * q[k]

    for k in range(m):
        for ell in range(k+1, m):
            qkl = Q[k, ell]
            K[k, ell] = K[ell, k] = 0.25 * qkl
            g[k] += -0.25 * qkl
            g[ell] += -0.25 * qkl
            c += 0.25 * qkl
    return K, g, c

def ising_value_from_bits(x, K, g, c=0.0):
    z = 1 - 2 * np.asarray(x)
    val = c + np.dot(g, z)
    m = len(z)
    for k in range(m):
        for ell in range(k+1, m):
            val += K[k, ell] * z[k] * z[ell]
    return float(val)
