import numpy as np 

def build_qubo(scenarios, alpha, costs, budget, eta):
    m = alpha.shape[0]
    B_lin = np.zeros(m)
    D_quad = np.zeros((m,m))
    A_const = 0.0

    for sc in scenarios :
        w = sc["weight"]
        T = sc["T"]
        n = T.shape[0]

        A_s = 0.0
        b_s = np.zeros(m)
        d_s = np.zeros((m,m))
        
        for i in range(n):
            for j in range(i + 1, n) :
                tij = T[i, j]
                if tij == 0.0:
                    continue
                A_s += tij
                a_vec = alpha[:, i, j]
                b_s -= tij * a_vec
                for k in range(m):
                    if a_vec[k] == 0.0:
                        continue
                    for ell in range(k+1, m):
                        if a_vec[ell] != 0.0:
                            d_s[k, ell] += tij * a_vec[k] * a_vec[ell]

        A_const += w * A_s 
        B_lin += w * b_s
        D_quad += w * d_s
        
    q = B_lin +eta * (costs**2 - 2.0 * budget * costs)
    Q = D_quad.copy()
    for k in range(m):
        for ell in range(k+1, m):
            Q[k, ell] += 2.0 * eta * costs[k] * costs[ell]

    const = A_const + eta * budget**2 
    return q, Q, const 

def qubo_value(x, q, Q, const=0.0):
    val = const + float(np.dot(q, x))
    m = len(x)
    for k in range(m):
        for ell in range(k+1,m):
            if Q[k,ell] != 0.0:
                val += Q[k,ell] * x[k] * x[ell]
    return val
      
    