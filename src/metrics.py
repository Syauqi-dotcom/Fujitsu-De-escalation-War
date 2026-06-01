import numpy as np
from typing import List, Dict, Union

def calculate_budget(syauqi_portfolio: np.ndarray, costs: np.ndarray) -> float:
    """
    Menghitung total biaya dari aksi yang dipilih (Persamaan 1).
    """
    return float(np.sum(costs * syauqi_portfolio))

def calculate_selected_actions(syauqi_portfolio: np.ndarray) -> int:
    """
    Menghitung jumlah aksi de-eskalasi yang diaktifkan (Persamaan 5).
    """
    return int(np.sum(syauqi_portfolio))

def calculate_scenario_risks(syauqi_portfolio: np.ndarray, scenarios: List[Dict], alpha: np.ndarray) -> np.ndarray:
    """
    Menghitung r_s(x) atau risiko residual untuk setiap skenario s.
    """
    m = len(syauqi_portfolio)
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
                    if syauqi_portfolio[k] == 1:
                        diminishing_factor *= (1.0 - alpha[k, i, j])
                
                r_s += T[i, j] * diminishing_factor
        risks.append(r_s)
        
    return np.array(risks)

def evaluate_robustness(syauqi_portfolio: np.ndarray, scenarios: List[Dict], alpha: np.ndarray) -> Dict[str, float]:
    """
    Menghitung MeanRisk, WorstRisk, dan RiskStd lintas skenario (Persamaan 6 & 7).
    """
    risks = calculate_scenario_risks(syauqi_portfolio, scenarios, alpha)
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
    Menghitung relative optimality gap (Bagian 10.4).
    """
    return (f_alg - f_exact_optimum) / (abs(f_exact_optimum) + 1e-12)