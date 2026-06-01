# from types import _ReturnT_co
from qulacs import Observable, QuantumCircuit, QuantumState
from scipy.optimize import minimize
from src.qubo import qubo_value
import numpy as np

def build_observable(K, g, gamma_tf=0.0):
    m = len(g)
    obs = Observable(m)

    for k in range(m):
        if abs(g[k]) > 1e-14:
            obs.add_operator(float(g[k]), f"Z {k}")
            
    for k in range(m):
        for ell in range(k+1, m):
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
        gamma=gammas[r]
        beta=betas[r]

        for k in range(m):
            angle = 2.0 * gamma * g[k]
            if abs(angle) > 1e-14:
                circuit.add_RZ_gate(k, angle)
        
        for k in range(m):
            for ell in range(k+1, m):
                angle = 2.0 * beta * K[k, ell]
                if abs(angle) > 1e-14:
                    circuit.add_CNOT_gate(k, ell)
                    circuit.add_RZ_gate(ell, angle)
                    circuit.add_CNOT_gate(k, ell)
        
        for k in range(m):
            circuit.add_RX_gate(k, 2.0 * beta)
    
    return circuit
        
def evaluate_energy_hva(params, K, g, observable):
    m = len(g)
    state = QuantumState(m)
    state.set_zero_state()
    circuit = build_hva_circuit(K, g, params)
    circuit.update_quantum_state(state)
    return observable.get_expectation_value(state).real

def build_hea_circuit(m, params, depth):
    circuit = QuantumCircuit(m)
    idx = 0 

    for k in range(m):
        circuit.add_RY_gate(k, params[idx])
        idx += 1
    
    for layer in range(depth):
        for k in range(m):
            circuit.add_RY_gate(k, params[idx])
            idx += 1
            circuit.add_RZ_gate(k, params[idx])
            idx += 1
    
        for k in range(m-1):
            circuit.add_CNOT_gate(k, k+1)
        circuit.add_CNOT_gate(m-1, 0)
    
    return circuit
    
def evaluate_energy_hea(params, m, depth, observable):
    state = QuantumState(m)
    state.set_zero_state()
    circuit = build_hea_circuit(m, params, depth)
    circuit.update_quantum_state(state)
    return observable.get_expectation_value(state).real

def run_hva_vqe(K, g, gamma_tf=0.2, depth=2, seed=123):
    rng = np.random.default_rng(seed)
    obs = build_observable(K, g, gamma_tf=gamma_tf)

    x0 = rng.uniform(low=-0.1, high=0.1, size=2 * depth)

    def objective(params):
        return evaluate_energy_hva(params, K, g, obs)

    res = minimize(
        objective,
        x0,
        method="COBYLA",
        options={"maxiter": 300, "rhobeg": 0.5, "tol": 1e-4},
    )
    return res 

def sample_hva_portfolios(K, g, params, n_shots=2000):
    m = len(g)
    state = QuantumState(m)
    state.set_zero_state()
    circuit = build_hva_circuit(K, g, params)
    circuit.update_quantum_state(state)

    samples = state.sampling(n_shots)
    X = np.zeros((n_shots, m), dtype=int)
    for r, integer_sample in enumerate(samples):
        for k in range(m):
            X[r, k] = (integer_sample >> k) & 1
    return X

def best_sampled_portfolios(samples, q, Q, const=0.0, top_k=10):
    unique = {}
    for x in samples:
        key = tuple(int(v) for v in x)
        if key not in unique:
            unique[key] = qubo_value(x, q, Q, const)
    ranked = sorted(unique.items(), key=lambda kv: kv[1])
    return ranked[:top_k]  
