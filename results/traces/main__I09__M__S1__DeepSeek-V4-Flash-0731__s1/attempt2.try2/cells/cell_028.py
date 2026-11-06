
import numpy as np

# Load data
thresholds = np.load('/tmp/thresholds.npy')  # raw thresholds (366, 60, 60)
climatology = np.load('/tmp/climatology.npy')  # raw climatology (366, 60, 60)
thr_smooth = np.load('/tmp/thr_smooth.npy')
cli_smooth = np.load('/tmp/cli_smooth.npy')
sea_cells = np.load('/tmp/sea_cells.npy')

n_lat, n_lon = sea_cells.shape
sea_indices = np.where(sea_cells)
sea_lats, sea_lons = sea_indices

# Check if any sea cells have NaN in raw thresholds/climatology
nan_raw_thr = 0
nan_raw_cli = 0
for si, sj in zip(sea_lats, sea_lons):
    if np.isnan(thresholds[:, si, sj]).any():
        nan_raw_thr += 1
    if np.isnan(climatology[:, si, sj]).any():
        nan_raw_cli += 1

print(f"Sea cells with NaN in raw thresholds: {nan_raw_thr}")
print(f"Sea cells with NaN in raw climatology: {nan_raw_cli}")

# Check for NaN in smoothed thresholds/climatology for sea cells
nan_sm_thr = 0
nan_sm_cli = 0
for si, sj in zip(sea_lats, sea_lons):
    if np.isnan(thr_smooth[:, si, sj]).any():
        nan_sm_thr += 1
    if np.isnan(cli_smooth[:, si, sj]).any():
        nan_sm_cli += 1

print(f"Sea cells with NaN in smoothed thresholds: {nan_sm_thr}")
print(f"Sea cells with NaN in smoothed climatology: {nan_sm_cli}")

# Check target doys specifically (153-244)
target_doy_start, target_doy_end = 153, 244
nan_target = 0
for si, sj in zip(sea_lats, sea_lons):
    if np.isnan(thresholds[target_doy_start-1:target_doy_end, si, sj]).any():
        nan_target += 1
print(f"Sea cells with NaN in raw thresholds for target doys (153-244): {nan_target}")
