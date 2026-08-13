import numpy as np
from typing import List, Dict, Union

def calculate_budget(action_selection: np.ndarray, costs: np.ndarray) -> float:
    """
    Menghitung total biaya dari vektor keputusan biner aksi.

    ``action_selection[k] = 1`` jika aksi ke-k dipilih, dan 0 jika tidak.
    """
    return float(np.sum(costs * action_selection))

def calculate_selected_actions(action_selection: np.ndarray) -> int:
    """
    Menghitung jumlah aksi de-eskalasi yang dipilih.

    ``action_selection`` adalah vektor keputusan biner x dengan x_k ∈ {0, 1}.
    """
    return int(np.sum(action_selection))

def calculate_scenario_risks(action_selection: np.ndarray, scenarios: List[Dict], alpha: np.ndarray) -> np.ndarray:
    """
    Menghitung risiko residual r_s(x) untuk setiap skenario s.

    ``action_selection`` merepresentasikan vektor keputusan biner x.
    """
    m = len(action_selection)
    risks = []
    
    for sc in scenarios:
        T = sc["T"]
        n = T.shape[0]
        r_s = 0.0
        
        for i in range(n):
            for j in range(i + 1, n):
                if T[i, j] == 0.0:
                    continue
                # Menghitung efek reduksi dari portofolio terhadap edge (i, j)
                diminishing_factor = 1.0
                for k in range(m):
                    if action_selection[k] == 1:
                        diminishing_factor *= (1.0 - alpha[k, i, j])
                
                r_s += T[i, j] * diminishing_factor
        risks.append(r_s)
        
    return np.array(risks)

def evaluate_robustness(action_selection: np.ndarray, scenarios: List[Dict], alpha: np.ndarray) -> Dict[str, float]:
    """
    Menghitung mean risk, worst-case risk, dan simpangan baku lintas skenario.

    ``action_selection`` merepresentasikan vektor keputusan biner x.
    """
    risks = calculate_scenario_risks(action_selection, scenarios, alpha)
    weights = np.array([sc["weight"] for sc in scenarios])
    
    mean_risk = np.sum(weights * risks)
    worst_risk = np.max(risks)
    variance = np.sum(weights * (risks - mean_risk)**2)
    risk_std = np.sqrt(variance)
    
    return {
        "mean_risk": float(mean_risk),
        "worst_risk": float(worst_risk),
        "risk_std": float(risk_std),
        "raw_risks": risks.tolist()
    }

def calculate_optimality_gap(f_alg: float, f_exact_optimum: float) -> float:
    """
    Menghitung relative optimality gap.
    """
    return (f_alg - f_exact_optimum) / (abs(f_exact_optimum) + 1e-12)
