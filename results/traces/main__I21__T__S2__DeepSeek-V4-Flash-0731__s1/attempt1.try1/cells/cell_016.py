
import numpy as np
import xarray as xr
import pandas as pd
from datetime import datetime, timedelta

# Load data
baseline_data = xr.open_dataset('baseline_data.nc')
target_data = xr.open_dataset('target_data.nc')

baseline_sst = baseline_data.analysed_sst.values
baseline_time = baseline_data.time.values
target_sst = target_data.analysed_sst.values

# Check: what are the dimensions and time ranges?
print("Baseline time:", baseline_time[0], "to", baseline_time[-1])
print("Baseline shape:", baseline_sst.shape)
print("Target time:", target_data.time.values[0], "to", target_data.time.values[-1])

# Check some SST values
print("\nSample baseline SST values (first few days, cell 0,0):")
for i in range(5):
    print(f"  {pd.Timestamp(baseline_time[i])}: {baseline_sst[i, 0, 0]}")
    
print("\nSample target SST values (first few days, cell 0,0):")
for i in range(5):
    print(f"  {pd.Timestamp(target_data.time.values[i])}: {target_sst[i, 0, 0]}")

# Check for NaN in target
print(f"\nNaN in target SST: {np.sum(~np.isfinite(target_sst))}")
print(f"NaN in baseline SST: {np.sum(~np.isfinite(baseline_sst))}")
