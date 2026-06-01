import numpy as np 

def generate_country_network(
    n_blocks=5,
    block_size=6,
    p_in=0.8,
    p_out=0.25,
    p_neg=0.7,
    j_in=(0.8, 1.2),
    j_out=(0.2, 0.8),
    j_out_pos=0.2,
    seed=123,
):
    rng = np.random.default_rng(seed)
    n = n_blocks * block_size
    block = np.repeat(np.arange(n_blocks), block_size)
    J = np.zeros((n,n), dtype=float)

    for i in range(n):
        for j in range(i+1, n):
            same = block[i] == block[j]
            if same : 
                if rng.random() < p_in:
                    val = rng.uniform(*j_in)
                else : 
                    val = 0.0
            else : 
                if rng.random() < p_out:
                    if rng.random() < p_neg:
                        val = -rng.uniform(*j_out)
                    else :
                        val = rng.uniform(0.0, j_out_pos)
                else : 
                    val = 0.0
            J[i,j] = J[j,i] = val
    return J, block

def tension_matrix(J):
    return np.maximum(0.0, -J)
                    

    