import numpy as np 

def build_action_effectiveness(block):
    n = len(block)
    n_blocks = int(block.max()) + 1
    actions_per_block = 6
    m = n_blocks * actions_per_block

    # (a_in, a_out) for sic action types
    eff = [
        (0.25, 0.10),
        (0.22, 0.10),
        (0.18, 0.08),
        (0.16, 0.07),
        (0.15, 0.05),
        (0.12, 0.05),
    ]

    alpha = np.zeros((m, n, n), dtype = float)

    for r in range(n_blocks):
        left = (r - 1) % n_blocks
        right = (r + 1) % n_blocks
        for a_type, (a_in, a_out) in enumerate(eff):
            k = r * actions_per_block + a_type
            for i in range(n):
                for j in range(i + 1, n):
                    bi, bj = block[i], block[j]
                    val = 0.0 
                    if bi == r and bj == r:
                        val = a_in
                    elif (bi == r and bj in [left, right]) or (bj == r and bi in [left, right]):
                        val = a_out
                    alpha[k, i, j] = alpha[k, j, i] = val
    return alpha 