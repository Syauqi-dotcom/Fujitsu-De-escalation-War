#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import os
import sys
import pickle
sys.path.append(os.path.abspath('..'))

import pickle
import numpy as np
from src.baselines import simulated_annealing, local_search
from src.qulacs_vqe import qubo_value


# In[ ]:


with open('results/raw/qubo_ising_data.pkl', 'rb') as f:
    data_n2 = pickle.load(f)
q, Q, const = data_n2['q'], data_n2['Q'], data_n2['const']


# In[ ]:


with open('results/raw/vqe_results.pkl', 'rb') as f:
    data_n3 = pickle.load(f)
vqe_best_energy = data_n3['best_energy']
print("Data QUBO dan hasil VQE berhasil di-load!")


# In[ ]:


print("\nMenjalankan Simulated Annealing...")
sa_x, sa_fx = simulated_annealing(q, Q, const, n_steps=20000)


# In[ ]:


print("Menjalankan Local Search dari bitstring acak...")
random_start = np.random.randint(0, 2, size=30)
ls_x = local_search(random_start, q, Q, max_sweeps=100)
ls_fx = qubo_value(ls_x, q, Q, const)


# In[ ]:


print(f"VQE (Quantum Simulator) : {vqe_best_energy:.4f}")
print(f"Simulated Annealing     : {sa_fx:.4f}")
print(f"Local Search            : {ls_fx:.4f}")

