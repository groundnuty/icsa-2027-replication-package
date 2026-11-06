
import numpy as np
from datetime import datetime, date, timedelta
from datetime import date as dt_date
from collections import defaultdict
import xarray as xr

# Re-verify the full pipeline with a focus on correctness
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

# Let me do a manual verification for one specific cell
# Pick cell at some lat/lon that is a sea cell

# First, identify a sea cell
target_time_idx = np.load('/tmp/target_time_idx.npy')
time = ds['time'].values

# Get the first sea cell
sea_cells = np.load('/tmp/sea_cells.npy')
sea_positions = np.where(sea_cells)
li, lo = sea_positions[0][0], sea_positions[1][0]
print(f"Checking sea cell at lat_idx={li} (lat={ds['latitude'].values[34+li]}), lon_idx={lo} (lon={ds['longitude'].values[213+lo]})")

# Load SST for this cell for the target period
target_sst = np.load('/tmp/target_sst.npy')
cell_sst = target_sst[:, li, lo].astype(np.float64)
print("SST values:", cell_sst[:5], "...", cell_sst[-5:])
print("Has NaN:", np.isnan(cell_sst).any())

# Load threshold for this cell
threshold_smooth = np.load('/tmp/threshold_smooth_correct.npy')
cell_thresh = threshold_smooth[:, li, lo]
print("Threshold values (first 5):", cell_thresh[:5])
print("Threshold NaN:", np.isnan(cell_thresh).any())

# Compute hot days for this cell
target_doy = np.load('/tmp/target_doy.npy')
target_doy_idx = target_doy - 1
cell_hot = cell_sst >= cell_thresh[target_doy_idx]
print("Hot days:", cell_hot.astype(int))
