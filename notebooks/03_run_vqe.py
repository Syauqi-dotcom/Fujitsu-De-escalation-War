#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os
import sys
import pickle
sys.path.append(os.path.abspath('..'))

import numpy as np
from src.qulacs_vqe import run_hva_vqe, sample_hva_portfolios, best_sampled_portfolios


# In[2]:


with open('results/raw/qubo_ising_data.pkl', 'rb') as f:
    data_n2 = pickle.load(f)

K, g = data_n2['K'], data_n2['g']
q, Q, const = data_n2['q'], data_n2['Q'], data_n2['const']
print("Data QUBO dan Ising berhasil di-load!")


# In[ ]:


print("Memulai optimasi VQE...")
vqe_res = run_hva_vqe(K, g, gamma_tf=0.2, depth=2)
print("VQE Energy:", vqe_res.fun)


# In[ ]:


n_shots = 2000
samples = sample_hva_portfolios(K, g, vqe_res.x, n_shots=n_shots)
top_quantum = best_sampled_portfolios(samples, q, Q, const, top_k=5)

print("\n--- Top 5 Portofolio Quantum (VQE) ---")
for idx, (bitstring, obj_val) in enumerate(top_quantum):
    selected_actions = sum(bitstring)
    print(f"Rank {idx+1} | Total Aksi: {selected_actions} | Objective: {obj_val:.4f}")


# In[ ]:


with open('results/raw/vqe_results.pkl', 'wb') as f:
    pickle.dump({
        'best_energy': vqe_res.fun, 
        'top_portfolios': top_quantum
    }, f)
print("\nHasil eksekusi VQE berhasil disimpan ke pickle!")

