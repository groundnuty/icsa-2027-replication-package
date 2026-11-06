
import xarray as xr
import numpy as np
import pandas as pd

# Load the output file
ds = xr.open_dataset('output/mhw_mask.nc')
times = ds.time.values
print("Time values in NetCDF:")
print(times[:5])
print(times[-5:])

# Check they are daily values from June 1 to Aug 31, 2019
expected_start = np.datetime64('2019-06-01')
expected_end = np.datetime64('2019-08-31')
print(f"\nFirst time: {times[0]}, expected: {expected_start}")
print(f"Last time: {times[-1]}, expected: {expected_end}")
print(f"Number of time steps: {len(times)}")
print(f"All times are midnight: {all(np.datetime64(t, 'D') == t for t in times)}")

# Verify consecutive days
diffs = np.diff(times.astype('datetime64[D]').astype('int64'))
print(f"Consecutive day differences: {np.unique(diffs)}")

# Verify the coordinates match the dataset
print(f"\nLat values: {ds.lat.values[:3]} ... {ds.lat.values[-3:]}")
print(f"Lon values: {ds.lon.values[:3]} ... {ds.lon.values[-3:]}")
