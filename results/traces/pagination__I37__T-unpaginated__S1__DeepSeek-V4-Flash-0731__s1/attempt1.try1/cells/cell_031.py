
import numpy as np
import datetime

# Load data
target_sst = np.load('work/target_sst.npy')
sea_mask = np.load('work/sea_mask.npy')
climatology_smooth = np.load('work/climatology_smooth.npy')
threshold_smooth = np.load('work/threshold_smooth.npy')

# Day of year mapping
def doy_from_date(date):
    month_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_days[date.month-1] + date.day

# Target dates
target_start = datetime.date(2012, 6, 1)
target_end = datetime.date(2012, 8, 31)
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += datetime.timedelta(days=1)

target_doy = np.array([doy_from_date(date) for date in target_dates])

n_lat, n_lon = 60, 60
climatology_3d = climatology_smooth.reshape(366, n_lat, n_lon)
threshold_3d = threshold_smooth.reshape(366, n_lat, n_lon)

# Get climatology for target days
clim_target = climatology_3d[target_doy - 1]  # (92, 60, 60)
thr_target = threshold_3d[target_doy - 1]

# Compute anomalies for sea cells
anomaly = target_sst - clim_target
sea_anomaly = anomaly[sea_mask[np.newaxis, :, :]]
print(f"Mean SST anomaly (2012 vs climatology): {np.mean(sea_anomaly):.4f} K")
print(f"Median SST anomaly: {np.median(sea_anomaly):.4f} K")
print(f"P10 anomaly: {np.percentile(sea_anomaly, 10):.4f} K")
print(f"P90 anomaly: {np.percentile(sea_anomaly, 90):.4f} K")

# Fraction of sea cell-days with positive anomaly
print(f"Fraction positive anomaly: {(sea_anomaly > 0).mean():.4f}")

# What's the typical threshold anomaly (threshold - climatology)?
thr_anom = thr_target - clim_target
sea_thr_anom = thr_anom[sea_mask[np.newaxis, :, :]]
print(f"\nMean (threshold - climatology): {np.mean(sea_thr_anom):.4f} K")
print(f"Min (threshold - climatology): {np.min(sea_thr_anom):.4f} K")
print(f"Max (threshold - climatology): {np.max(sea_thr_anom):.4f} K")

# How close does the SST get to the threshold?
diff = thr_target - target_sst
sea_diff = diff[sea_mask[np.newaxis, :, :]]
print(f"\nMean (threshold - SST): {np.mean(sea_diff):.4f} K")
print(f"Min (threshold - SST): {np.min(sea_diff):.4f} K")
print(f"Fraction where SST >= threshold: {(sea_diff <= 0).mean():.6f}")
