
import numpy as np
import pandas as pd
from datetime import date

def day_of_year_custom(dt):
    month = dt.month
    day = dt.day
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

# Load saved data
threshold = np.load('/tmp/threshold_smoothed.npy')
climatology = np.load('/tmp/climatology_smoothed.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
per_cell_mhw = np.load('/tmp/per_cell_mhw.npy')
tgt_data = np.load('/tmp/tgt_data.npy')
tgt_doy = np.load('/tmp/tgt_doy.npy')

# Check sea cell threshold/climatology values
print("Sea cell check:")
print(f"Sea cell count: {sea_cells.sum()}")

# Find first sea cell
lat_idx, lon_idx = np.where(sea_cells)
print(f"First sea cell at ({lat_idx[0]}, {lon_idx[0]})")

# Check threshold values for this cell
cell_threshold = threshold[:, lat_idx[0], lon_idx[0]]
cell_clim = climatology[:, lat_idx[0], lon_idx[0]]
print(f"Threshold range: {np.nanmin(cell_threshold):.2f} to {np.nanmax(cell_threshold):.2f}")
print(f"Climatology range: {np.nanmin(cell_clim):.2f} to {np.nanmax(cell_clim):.2f}")

# Check for NaN in sea cells
thresh_sea = threshold[:, sea_cells]
print(f"\nThreshold NaN count in sea cells: {np.isnan(thresh_sea).sum()}")
print(f"Climatology NaN count in sea cells: {np.isnan(climatology[:, sea_cells]).sum()}")

# Check target data values
print(f"\nTarget data range: {np.nanmin(tgt_data):.2f} to {np.nanmax(tgt_data):.2f}")

# Check hot day detection for this cell
lat0, lon0 = lat_idx[0], lon_idx[0]
tgt_series = tgt_data[:, lat0, lon0]
thresh_series = threshold[tgt_doy - 1, lat0, lon0]
hot_series = tgt_series >= thresh_series

print(f"\nFirst sea cell at ({lat0}, {lon0}):")
print(f"Target SST values: {tgt_series}")
print(f"Threshold values: {thresh_series}")
print(f"Hot: {hot_series}")
print(f"Per-cell MHW: {per_cell_mhw[:, lat0, lon0]}")
