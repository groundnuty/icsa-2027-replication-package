
import numpy as np
import pandas as pd
from datetime import timedelta

# Load data
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
sea_mask = np.load('/tmp/sea_mask.npy')
target_sst = np.load('/tmp/target_sst.npy')
target_time = np.load('/tmp/target_time.npy')
hot = np.load('/tmp/hot.npy')

def doy_from_date(dt):
    month_days_cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_days_cum[dt.month - 1] + dt.day

target_dates = [pd.Timestamp(t).to_pydatetime() for t in target_time]
target_doy = np.array([doy_from_date(d) for d in target_dates])
target_sst64 = target_sst.astype(np.float64)

# Check a specific sea cell
sea_indices = np.where(sea_mask)
lat_i, lon_j = sea_indices[0][0], sea_indices[1][0]

print(f"Cell ({lat_i}, {lon_j})")
print(f"Sea cell: {sea_mask[lat_i, lon_j]}")

# Check day 30 (July 1, DOY 183)
t = 30
doy = target_doy[t]
thr = threshold_smooth[doy-1, lat_i, lon_j]
sst = target_sst64[t, lat_i, lon_j]
is_hot = hot[t, lat_i, lon_j]
print(f"\nDay {target_dates[t].strftime('%Y-%m-%d')} (DOY {doy}):")
print(f"  SST: {sst:.2f}, Threshold: {thr:.2f}")
print(f"  Hot (SST >= threshold): {sst >= thr}, Computed hot: {is_hot}")
print(f"  Match: {(sst >= thr) == is_hot}")

# Check day 0 (June 1, DOY 153)
t = 0
doy = target_doy[t]
thr = threshold_smooth[doy-1, lat_i, lon_j]
sst = target_sst64[t, lat_i, lon_j]
is_hot = hot[t, lat_i, lon_j]
print(f"\nDay {target_dates[t].strftime('%Y-%m-%d')} (DOY {doy}):")
print(f"  SST: {sst:.2f}, Threshold: {thr:.2f}")
print(f"  Hot (SST >= threshold): {sst >= thr}, Computed hot: {is_hot}")
print(f"  Match: {(sst >= thr) == is_hot}")
