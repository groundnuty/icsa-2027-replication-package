
import numpy as np
import pickle

base_data = np.load('/work/base_data.npy')
tgt_data = np.load('/work/tgt_data.npy')
with open('/work/pool_dates.pkl', 'rb') as f:
    pool_dates = pickle.load(f)

# Check NaN patterns in base and tgt
base_nan = np.isnan(base_data)
tgt_nan = np.isnan(tgt_data)

# Per-cell: is there any NaN in base?
cell_base_nan = base_nan.any(axis=0)  # (60,60)
# Per-cell: is there any NaN in target?
cell_tgt_nan = tgt_nan.any(axis=0)  # (60,60)

print("Cells with any NaN in baseline:", cell_base_nan.sum())
print("Cells with any NaN in target:", cell_tgt_nan.sum())

# Sea cells: finite on every day of target period
sea_cells = ~cell_tgt_nan
print("Sea cells:", sea_cells.sum())

# Check overlap
print("Cells NaN in base but sea in target:", (cell_base_nan & sea_cells).sum())
print("Cells sea in base but NaN in target:", (~cell_base_nan & ~sea_cells).sum())

# Are sea cells a subset of cells with finite baseline?
print("All sea cells have finite baseline?", np.all(~cell_base_nan[sea_cells]))
