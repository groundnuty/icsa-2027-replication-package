import numpy as np
from datetime import datetime, timedelta

# Load data
target_sst = np.load('/tmp/target_sst.npy')  # (92, 60, 60)
sea_mask = np.load('/tmp/sea_mask.npy')  # (60, 60)
sea_indices = np.load('/tmp/sea_indices.npy')  # (n_sea, 2)
threshold_smooth = np.load('/tmp/threshold_smooth.npy')  # (366, n_sea)
clim_smooth = np.load('/tmp/clim_smooth.npy')  # (366, n_sea)

n_sea = sea_indices.shape[0]
n_target = target_sst.shape[0]

# Target dates
target_start = datetime(2019, 6, 1)
target_dates = []
d = target_start
while d <= datetime(2019, 8, 31):
    target_dates.append(d)
    d += timedelta(days=1)

def day_of_year(date):
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[date.month - 1] + date.day

# Get day of year for each target date
target_doy = np.array([day_of_year(d) for d in target_dates])
print(f"Target DOYs: {target_doy}")

# Extract target SST for sea cells: (n_sea, n_target)
target_sst_sea = np.zeros((n_sea, n_target), dtype=np.float64)
for c, (lat_i, lon_j) in enumerate(sea_indices):
    target_sst_sea[c] = target_sst[:, lat_i, lon_j]

print(f"Target SST for sea cells: {target_sst_sea.shape}")

# Get thresholds for each sea cell at each target day
# threshold_smooth is (366, n_sea), indexed by doy-1
threshold_target = np.zeros((n_sea, n_target), dtype=np.float64)
for t, doy in enumerate(target_doy):
    threshold_target[:, t] = threshold_smooth[doy - 1, :]

# Determine hot days: SST >= threshold
hot = target_sst_sea >= threshold_target
print(f"Hot days: {hot.sum()}/{n_sea * n_target}")
np.save('/tmp/hot.npy', hot)
