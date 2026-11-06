
import pandas as pd
import numpy as np

all_dates = pd.date_range('1982-01-01', '2023-12-31', freq='D')

# Extended baseline indices in the full dataset
ext_start = pd.Timestamp('1991-12-27')
ext_end = pd.Timestamp('2003-01-05')
ext_mask = (all_dates >= ext_start) & (all_dates <= ext_end)
ext_idx = np.where(ext_mask)[0]
print(f"Extended baseline indices: {ext_idx[0]} to {ext_idx[-1]}, count: {len(ext_idx)}")

# Baseline indices
base_start = pd.Timestamp('1992-01-01')
base_end = pd.Timestamp('2002-12-31')
base_mask = (all_dates >= base_start) & (all_dates <= base_end)
base_idx = np.where(base_mask)[0]
print(f"Baseline indices: {base_idx[0]} to {base_idx[-1]}, count: {len(base_idx)}")

# Target indices
tgt_start = pd.Timestamp('2012-06-01')
tgt_end = pd.Timestamp('2012-08-31')
tgt_mask = (all_dates >= tgt_start) & (all_dates <= tgt_end)
tgt_idx = np.where(tgt_mask)[0]
print(f"Target indices: {tgt_idx[0]} to {tgt_idx[-1]}, count: {len(tgt_idx)}")
