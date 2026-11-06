
import numpy as np
import pandas as pd

# Load saved data
baseline_sst = np.load('/work/baseline_sst.npy')  # (4028, 60, 60)
target_sst = np.load('/work/target_sst.npy')  # (92, 60, 60)
baseline_times = np.load('/work/baseline_times.npy')
target_times = np.load('/work/target_times.npy')

print(f"Baseline SST: {baseline_sst.shape}")
print(f"Target SST: {target_sst.shape}")
print(f"Baseline times: {baseline_times[0]} to {baseline_times[-1]}")
print(f"Target times: {target_times[0]} to {target_times[-1]}")

# Convert times to pandas
baseline_pd = pd.to_datetime(baseline_times)
target_pd = pd.to_datetime(target_times)

print(f"Baseline pd: {baseline_pd[0]} to {baseline_pd[-1]}, len={len(baseline_pd)}")
print(f"Target pd: {target_pd[0]} to {target_pd[-1]}, len={len(target_pd)}")

# Define DOY function
def doy(date):
    """Map a date to day of year 1-366 using leap-year numbering."""
    dt = pd.Timestamp(date)
    month = dt.month
    day = dt.day
    month_lengths = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_lengths[:month-1]) + day

# Compute DOY for each baseline date
baseline_doy = np.array([doy(d) for d in baseline_pd])
print(f"Baseline DOY range: {baseline_doy.min()} to {baseline_doy.max()}")

# Also compute DOY for each target date
target_doy = np.array([doy(d) for d in target_pd])
print(f"Target DOY range: {target_doy.min()} to {target_doy.max()}")
