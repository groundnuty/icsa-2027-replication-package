import h5py
import numpy as np
from datetime import datetime, timedelta

f = h5py.File('/work/sst_s2.nc', 'r')
time_raw = f['time'][:]

# Convert using seconds since 1981-01-01
epoch = datetime(1981, 1, 1)
dates = [epoch + timedelta(seconds=int(t)) for t in time_raw]
print("First date:", dates[0])
print("Last date:", dates[-1])
print("Number of days:", len(dates))

# Find baseline and target indices
baseline_start = datetime(1991, 12, 27)
baseline_end = datetime(2003, 1, 5)
target_start = datetime(2007, 6, 1)
target_end = datetime(2007, 8, 31)

# Find indices
base_indices = [i for i, d in enumerate(dates) if baseline_start <= d <= baseline_end]
targ_indices = [i for i, d in enumerate(dates) if target_start <= d <= target_end]

print(f"Baseline indices: {base_indices[0]} to {base_indices[-1]}, count={len(base_indices)}")
print(f"  First baseline date: {dates[base_indices[0]]}")
print(f"  Last baseline date: {dates[base_indices[-1]]}")
print(f"Target indices: {targ_indices[0]} to {targ_indices[-1]}, count={len(targ_indices)}")
print(f"  First target date: {dates[targ_indices[0]]}")
print(f"  Last target date: {dates[targ_indices[-1]]}")
