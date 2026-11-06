
import numpy as np
import pandas as pd
from datetime import timedelta

threshold_smooth = np.load('/tmp/threshold_smooth.npy')
climatology_smooth = np.load('/tmp/climatology_smooth.npy')
sea_mask = np.load('/tmp/sea_mask.npy')
target_sst = np.load('/tmp/target_sst.npy')
target_time = np.load('/tmp/target_time.npy')

# Day-of-year function
def doy_from_date(dt):
    month_days_cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_days_cum[dt.month - 1] + dt.day

# Get target dates as datetime
target_dates = [pd.Timestamp(t).to_pydatetime() for t in target_time]
target_doy = np.array([doy_from_date(d) for d in target_dates])
print("Target DOYs:", target_doy)
print("Target date range:", target_dates[0], "to", target_dates[-1])

# Convert target SST to float64
target_sst64 = target_sst.astype(np.float64)
print("target_sst64 shape:", target_sst64.shape)

# For each sea cell, check if each target day is hot
# A day is hot if SST >= threshold for that DOY

n_time = len(target_dates)
n_lat, n_lon = 60, 60

# Create hot matrix: (time, lat, lon) with True/False
hot = np.zeros((n_time, n_lat, n_lon), dtype=bool)

for t in range(n_time):
    doy = target_doy[t] - 1  # 0-indexed
    thr = threshold_smooth[doy]  # shape (60, 60)
    sst_t = target_sst64[t]  # shape (60, 60)
    hot[t] = (sst_t >= thr) & sea_mask

print("Hot days count:", hot.sum())
print("Hot days per time step:", hot.sum(axis=(1,2)))
