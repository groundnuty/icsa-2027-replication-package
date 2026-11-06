
import numpy as np
import pickle

# Load all saved intermediate results
target_data = np.load('/tmp/target_data.npy')
cell_mhw = np.load('/tmp/cell_mhw.npy')
sea_mask = np.load('/tmp/sea_mask.npy')

with open('/tmp/dates.pkl', 'rb') as f:
    dates = pickle.load(f)
target_dates = dates['target_dates']
baseline_dates = dates['baseline_dates']

print(f"target_data shape: {target_data.shape}")
print(f"cell_mhw shape: {cell_mhw.shape}")
print(f"sea_mask shape: {sea_mask.shape}")
print(f"target dates: {len(target_dates)}, {target_dates[0]} to {target_dates[-1]}")
print(f"baseline dates: {len(baseline_dates)}, {baseline_dates[0]} to {baseline_dates[-1]}")

# Verify cell_mhw is all zeros
print(f"cell_mhw sum: {cell_mhw.sum()}")
print(f"Any cell in MHW: {cell_mhw.any()}")
print(f"Sea cells: {sea_mask.sum()}")
