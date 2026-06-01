import numpy as np 

def build_scenarios(T, block, delta_border=1.0, delta_internal=0.7):
    n_blocks = int(block.max()) + 1
    scenarios = []

    # Border scenarios on a ring
    for a in range(n_blocks):
        b =  (a+1) % n_blocks
        Ts = T.copy()
        mask_a = np.where(block == a)[0]
        mask_b = np.where(block == b)[0]
        for i in mask_a:
            for j in mask_b:
                Ts[i, j] *= (1.0 + delta_border)
                Ts[j, i] *= (1.0 + delta_border)
        scenarios.append({"name": f"border_{a}_{b}","weight": 0.12, "T": Ts})

    # Internal shock scenarios
    for a in range(n_blocks):
        Ts = T.copy()
        mask = np.where(block == a)[0]
        for idx_i, i in enumerate(mask):
            for j in mask[idx_i + 1:]:
                Ts[i,j] *= (1.0 + delta_internal)
                Ts[j,i] *= (1.0 + delta_internal)
        scenarios.append({"name": f"internal_{a}", "weight": 0.08, "T": Ts})
    
    total_w = sum(s["weight"] for s in scenarios)
    for s in scenarios:
        s["weight"] /= total_w

    return scenarios
