
import pandas as pd
import numpy as np

all_dates = pd.date_range('1982-01-01', '2023-12-31', freq='D')

# Find indices for:
# 1. Extended baseline: 1991-12-27 to 2003-01-05
baseline_start = pd.Timestamp('1991-12-27')
baseline_end = pd.Timestamp('2003-01-05')
baseline_idx = np.where((all_dates >= baseline_start) & (all_dates <= baseline_end))[0]
print(f"Baseline indices: {baseline_idx[0]} to {baseline_idx[-1]}, count: {len(baseline_idx)}")
print(f"Baseline dates: {all_dates[baseline_idx[0]]} to {all_dates[baseline_idx[-1]]}")

# 2. Target period: 2012-06-01 to 2012-08-31
target_start = pd.Timestamp('2012-06-01')
target_end = pd.Timestamp('2012-08-31')
target_idx = np.where((all_dates >= target_start) & (all_dates <= target_end))[0]
print(f"Target indices: {target_idx[0]} to {target_idx[-1]}, count: {len(target_idx)}")
print(f"Target dates: {all_dates[target_idx[0]]} to {all_dates[target_idx[-1]]}")

# 3. Full 1992-2002 baseline range
base92_start = pd.Timestamp('1992-01-01')
base92_end = pd.Timestamp('2002-12-31')
print(f"Number of baseline dates (1992-2002): {len(np.where((all_dates >= base92_start) & (all_dates <= base92_end))[0])}")
print(f"Number of days in extended baseline: {len(baseline_idx)}")
