
import numpy as np
import pandas as pd

# Load baseline data
baseline_sst = np.load('/work/baseline_sst.npy')  # (4028, 60, 60)
baseline_time = np.load('/work/baseline_time.npy', allow_pickle=True)
target_sst = np.load('/work/target_sst.npy')  # (92, 60, 60)
target_time = np.load('/work/target_time.npy', allow_pickle=True)

bt = pd.to_datetime(baseline_time)
tt = pd.to_datetime(target_time)

print("baseline time range:", bt[0], "to", bt[-1])
print("target time range:", tt[0], "to", tt[-1])
print("baseline shape:", baseline_sst.shape)
print("target shape:", target_sst.shape)

# Check for NaN in baseline and target
print("baseline NaN count:", np.isnan(baseline_sst).sum())
print("target NaN count:", np.isnan(target_sst).sum())

# Verify time step is 1 day
print("baseline time diffs (first 10):", np.diff(bt).astype('timedelta64[D]')[:10])
print("target time diffs (first 5):", np.diff(tt).astype('timedelta64[D]')[:5])
