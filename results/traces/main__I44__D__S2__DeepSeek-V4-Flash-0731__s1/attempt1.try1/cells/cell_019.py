
import numpy as np

thresholds = np.load('/work/thresholds.npy')
climatology = np.load('/work/climatology.npy')
thresholds_smooth = np.load('/work/thresholds_smooth.npy')
climatology_smooth = np.load('/work/climatology_smooth.npy')
sea_cells = np.load('/work/sea_cells.npy')

# Check for NaN in sea cell thresholds/climatology (before smoothing)
sea_indices = np.argwhere(sea_cells)
print("Sea cells with NaN thresholds (before smoothing):")
count = 0
for lat_i, lon_i in sea_indices:
    if np.any(np.isnan(thresholds[lat_i, lon_i])):
        nan_doys = np.where(np.isnan(thresholds[lat_i, lon_i]))[0] + 1
        print(f"  Cell ({lat_i},{lon_i}): NaN doys {nan_doys}")
        count += 1
if count == 0:
    print("  None")

print("\nSea cells with NaN climatology (before smoothing):")
count = 0
for lat_i, lon_i in sea_indices:
    if np.any(np.isnan(climatology[lat_i, lon_i])):
        nan_doys = np.where(np.isnan(climatology[lat_i, lon_i]))[0] + 1
        print(f"  Cell ({lat_i},{lon_i}): NaN doys {nan_doys}")
        count += 1
if count == 0:
    print("  None")

# Check for NaN in smoothed values
print("\nSea cells with NaN thresholds (after smoothing):")
count = 0
for lat_i, lon_i in sea_indices:
    if np.any(np.isnan(thresholds_smooth[lat_i, lon_i])):
        nan_doys = np.where(np.isnan(thresholds_smooth[lat_i, lon_i]))[0] + 1
        print(f"  Cell ({lat_i},{lon_i}): NaN doys {nan_doys}")
        count += 1
if count == 0:
    print("  None")
