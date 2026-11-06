
import numpy as np

thr_smooth = np.load('/tmp/thr_smooth.npy')
cli_smooth = np.load('/tmp/cli_smooth.npy')
sea_cells = np.load('/tmp/sea_cells.npy')

# Check if sea cells have NaN in smoothed thresholds/climatology for target doys
# Target doys are 153-244
n_lat, n_lon = sea_cells.shape

sea_indices = np.where(sea_cells)
sea_lats, sea_lons = sea_indices

# Check each sea cell for NaN in smoothed thresholds for all doys
nan_cells = []
for si, sj in zip(sea_lats, sea_lons):
    if np.isnan(thr_smooth[:, si, sj]).any():
        nan_cells.append((si, sj, np.isnan(thr_smooth[:, si, sj]).sum()))

print(f"Sea cells with NaN in smoothed thresholds: {len(nan_cells)}")
if nan_cells:
    for nc in nan_cells[:10]:
        print(f"  Cell ({nc[0]}, {nc[1]}): {nc[2]} NaN doys")

# Check for target doys specifically (153-244)
target_doy_start, target_doy_end = 153, 244
nan_target = 0
for si, sj in zip(sea_lats, sea_lons):
    if np.isnan(thr_smooth[target_doy_start-1:target_doy_end, si, sj]).any():
        nan_target += 1
print(f"Sea cells with NaN thresholds in target doys: {nan_target}")
