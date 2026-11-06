
import numpy as np
import pickle

# Load state
sea_cells = np.load('/work/sea_cells.npy')
threshold_smoothed = np.load('/work/threshold_smoothed.npy')
climatology_smoothed = np.load('/work/climatology_smoothed.npy')
target_sst = np.load('/work/target_sst.npy')

with open('/work/target_dates.pkl', 'rb') as f:
    target_dates = pickle.load(f)

def day_of_year(date):
    month = date.month
    day = date.day
    cum_days_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days_before[month - 1] + day

target_doy = [day_of_year(d) for d in target_dates]

# Check if all sea cells have finite threshold for all target day DOYs
sea_idx = np.where(sea_cells)
n_sea = len(sea_idx[0])

all_finite = True
for k in range(n_sea):
    i, j = sea_idx[0][k], sea_idx[1][k]
    for doy in set(target_doy):
        idx = doy - 1
        if not np.isfinite(threshold_smoothed[idx, i, j]):
            print(f"Cell ({i},{j}) has non-finite threshold for doy={doy}")
            all_finite = False

if all_finite:
    print("All sea cells have finite thresholds for all target DOYs")

# Also check climatology
all_finite_clim = True
for k in range(n_sea):
    i, j = sea_idx[0][k], sea_idx[1][k]
    for doy in set(target_doy):
        idx = doy - 1
        if not np.isfinite(climatology_smoothed[idx, i, j]):
            print(f"Cell ({i},{j}) has non-finite climatology for doy={doy}")
            all_finite_clim = False

if all_finite_clim:
    print("All sea cells have finite climatology for all target DOYs")

# Check how many sea cells have any NaN in the target SST
n_nan_cells = 0
for k in range(n_sea):
    i, j = sea_idx[0][k], sea_idx[1][k]
    if not np.all(np.isfinite(target_sst[:, i, j])):
        n_nan_cells += 1
print(f"Sea cells with any NaN in target SST: {n_nan_cells}")
