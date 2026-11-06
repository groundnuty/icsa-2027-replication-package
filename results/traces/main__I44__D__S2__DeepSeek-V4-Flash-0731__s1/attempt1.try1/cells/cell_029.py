
import numpy as np
import pandas as pd

# Load thresholds and climatology
thresholds_smooth = np.load('/work/thresholds_smooth.npy')
climatology_smooth = np.load('/work/climatology_smooth.npy')
sea_cells = np.load('/work/sea_cells.npy')
target_data = np.load('/work/target_data.npy')

# Get sea cell indices
sea_indices = np.argwhere(sea_cells)

# Target doys (Jun 1 = 153 to Aug 31 = 244)
target_doys = np.arange(153, 245)  # 92 values

# Get thresholds for target period for all sea cells
# thresholds_smooth[lat, lon, doy-1]
# For each sea cell, get the thresholds for each target doy
target_thresholds = np.zeros((len(sea_indices), len(target_doys)))
target_clim = np.zeros((len(sea_indices), len(target_doys)))

for i, (lat_i, lon_i) in enumerate(sea_indices):
    target_thresholds[i] = thresholds_smooth[lat_i, lon_i, target_doys - 1]
    target_clim[i] = climatology_smooth[lat_i, lon_i, target_doys - 1]

print("Target period threshold stats (sea cells):")
print(f"  Min: {np.nanmin(target_thresholds):.2f} K")
print(f"  Max: {np.nanmax(target_thresholds):.2f} K")
print(f"  Mean: {np.nanmean(target_thresholds):.2f} K")

print("\nTarget period climatology stats:")
print(f"  Min: {np.nanmin(target_clim):.2f} K")
print(f"  Max: {np.nanmax(target_clim):.2f} K")
print(f"  Mean: {np.nanmean(target_clim):.2f} K")

# Target SST values
sea_target = target_data[:, sea_indices[:, 0], sea_indices[:, 1]]
print(f"\nTarget SST stats (sea cells):")
print(f"  Min: {np.nanmin(sea_target):.2f} K")
print(f"  Max: {np.nanmax(sea_target):.2f} K")
print(f"  Mean: {np.nanmean(sea_target):.2f} K")

# Check if SST values are reasonable for the Baltic Sea in summer
# Typical Baltic Sea summer SST is ~15-20°C = 288-293 K
# So our values around 280-292 K seem reasonable

# Verify the MHW detection by checking one cell that's in an MHW
mhw_mask = np.load('/work/mhw_mask.npy')
cells_in_mhw = np.argwhere(mhw_mask.sum(axis=0) > 0)
print(f"\nCells in MHW: {len(cells_in_mhw)}")

# Check a specific cell
lat_i, lon_i = cells_in_mhw[0]
print(f"\nCell ({lat_i}, {lon_i}):")
print(f"  MHW days: {np.where(mhw_mask[:, lat_i, lon_i] == 1)[0]}")

# Check its SST during MHW vs threshold
for t in np.where(mhw_mask[:, lat_i, lon_i] == 1)[0]:
    d_idx = target_doys[t] - 1
    sst = target_data[t, lat_i, lon_i]
    thresh = thresholds_smooth[lat_i, lon_i, d_idx]
    print(f"  Day {t} (doy {target_doys[t]}): SST={sst:.2f} K, threshold={thresh:.2f} K, diff={sst-thresh:.2f}")
