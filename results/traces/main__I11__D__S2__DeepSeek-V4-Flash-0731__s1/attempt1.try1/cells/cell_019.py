
import numpy as np
from datetime import date
import xarray as xr
import pandas as pd

# Reload everything needed
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
region = ds.sel(latitude=slice(55.67, 56.87), longitude=slice(16.45, 17.65))

target = region.sel(time=slice('2021-06-01', '2021-08-31'))
target_sst = target.analysed_sst.values.astype(np.float64)
target_dates = pd.to_datetime(target.time.values).date

# Load saved results
threshold_smooth = np.load('/work/threshold_smooth.npy')
climatology_smooth = np.load('/work/climatology_smooth.npy')
sea_mask = np.load('/work/sea_mask.npy')

print("Target SST shape:", target_sst.shape)
print("Sea mask shape:", sea_mask.shape)
print("Threshold shape:", threshold_smooth.shape)

# Day of year mapping
CUM = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
def doy_from_md(month, day):
    return CUM[month-1] + day

def get_doy(d):
    return doy_from_md(d.month, d.day)

# Get day of year for each target date
target_doy = np.array([get_doy(d) for d in target_dates])
print("Target DOYs:", target_doy)

# For each sea cell, check if hot on each target day
# hot[cell_i, cell_j, t] = 1 if SST >= threshold[doy[t]] for that cell
n_time = len(target_dates)
hot = np.zeros((60, 60, n_time), dtype=bool)

for t in range(n_time):
    doy = target_doy[t]
    # threshold_smooth[doy-1] is the threshold for day-of-year doy
    hot[:, :, t] = (target_sst[t] >= threshold_smooth[doy-1]) & sea_mask

print("Hot days count:", hot.sum())
print("Hot per time step:", hot.sum(axis=(0,1)))
