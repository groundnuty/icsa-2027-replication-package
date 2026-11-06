
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

baseline_time = np.load('/tmp/baseline_time.npy')

# Find which indices are in the strict baseline (1992-01-01 to 2002-12-31)
baseline_start = np.datetime64('1992-01-01')
baseline_end = np.datetime64('2002-12-31')
strict_mask = (baseline_time >= baseline_start) & (baseline_time <= baseline_end)
strict_idx = np.where(strict_mask)[0]
print(f"Strict baseline indices: {strict_idx[0]} to {strict_idx[-1]}, count: {len(strict_idx)}")
print(f"Dates: {baseline_time[strict_idx[0]]} to {baseline_time[strict_idx[-1]]}")

# Extension indices
ext_start = (baseline_time < baseline_start)
ext_end = (baseline_time > baseline_end)
print(f"Extension before: {np.sum(ext_start)} dates, from {baseline_time[ext_start][0]} to {baseline_time[ext_start][-1]}")
print(f"Extension after: {np.sum(ext_end)} dates, from {baseline_time[ext_end][0]} to {baseline_time[ext_end][-1]}")
