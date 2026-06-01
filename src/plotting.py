import numpy as np
import matplotlib.pyplot as plt
from typing import List, Dict

def plot_vqe_convergence(energy_history: List[float], save_path: str = None):
    """
    Membuat plot kurva konvergensi energi VQE dari optimizer.
    """
    plt.figure(figsize=(8, 5))
    plt.plot(energy_history, marker='o', linestyle='-', color='b', markersize=4)
    plt.title("VQE Optimizer Energy Convergence")
    plt.xlabel("Optimizer Iteration")
    plt.ylabel("Expectation Value (Energy)")
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300)
    plt.show()

def plot_risk_vs_budget(portfolios_data: List[Dict], save_path: str = None):
    """
    Membuat scatter plot antara Risk Reduction vs Budget.
    portfolios_data adalah list of dictionary berisi 'budget' dan 'risk'.
    """
    budgets = [p["budget"] for p in portfolios_data]
    risks = [p["risk"] for p in portfolios_data]
    
    plt.figure(figsize=(8, 5))
    plt.scatter(budgets, risks, color='r', alpha=0.7, edgecolor='k')
    plt.title("Risk Proxy vs. Budget Limit")
    plt.xlabel("Portfolio Budget Utilized")
    plt.ylabel("Risk Proxy (Lower is better)")
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300)
    plt.show()

def plot_scenario_robustness_boxplot(syauqi_portfolio_risks: np.ndarray, baseline_risks: np.ndarray, save_path: str = None):
    """
    Membuat boxplot untuk membandingkan robustness antar skenario stres.
    """
    data = [baseline_risks, syauqi_portfolio_risks]
    labels = ["Classical Baseline", "VQE Portfolio"]
    
    plt.figure(figsize=(7, 5))
    plt.boxplot(data, labels=labels, patch_artist=True, 
                boxprops=dict(facecolor='lightblue', color='blue'),
                medianprops=dict(color='red', linewidth=2))
    plt.title("Robustness Across Stress Scenarios")
    plt.ylabel("Scenario Risk $r_s(x)$")
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300)
    plt.show()

def plot_portfolio_objective_histogram(sampled_objectives: List[float], save_path: str = None):
    """
    Membuat histogram untuk mendistribusikan nilai objektif dari bitstrings yang disampel.
    """
    plt.figure(figsize=(8, 5))
    plt.hist(sampled_objectives, bins=30, color='purple', alpha=0.7, edgecolor='black')
    plt.title("Distribution of Sampled Portfolio Objectives")
    plt.xlabel("QUBO Objective Value $F(x)$")
    plt.ylabel("Frequency")
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300)
    plt.show()