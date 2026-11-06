
import numpy as np
import pandas as pd
import datetime

# Load saved data
baseline_data = np.load('/tmp/baseline_data.npy')  # (4028, 60, 60) float64
target_data = np.load('/tmp/target_data.npy')      # (92, 60, 60) float64
baseline_times = pd.DatetimeIndex(np.load('/tmp/baseline_times.npy').astype('datetime64[ns]'))
target_times = pd.DatetimeIndex(np.load('/tmp/target_times.npy').astype('datetime64[ns]'))
lat_values = np.load('/tmp/lat_values.npy')
lon_values = np.load('/tmp/lon_values.npy')

print("Baseline:", baseline_times[0], "to", baseline_times[-1], "n=", len(baseline_times))
print("Target:", target_times[0], "to", target_times[-1], "n=", len(target_times))
print("Shapes:", baseline_data.shape, target_data.shape)

# Check for NaNs
print("Baseline NaN count:", np.isnan(baseline_data).sum())
print("Target NaN count:", np.isnan(target_data).sum())

# Step 1: Sea cells - finite SST on every day of target period
sea_mask = np.all(~np.isnan(target_data), axis=0)  # (60, 60) bool
print("Sea cells:", sea_mask.sum(), "out of", sea_mask.size)
