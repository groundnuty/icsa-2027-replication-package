
import xarray as xr
import numpy as np
import pandas as pd

ds_out = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds_out['mhw'].values

# Check July 2 (index 31, since June 1 = 0)
# June 1 = index 0, so July 1 = index 30, July 2 = index 31
time_vals = pd.to_datetime(ds_out.time.values)
jul2_idx = np.where(time_vals == pd.Timestamp('2009-07-02'))[0][0]
print(f"July 2 index: {jul2_idx}")
print(f"Cells in MHW on July 2: {mhw[jul2_idx].sum()}")

# Total 1s in mask
print(f"Total 1s in mask: {mhw.sum()}")

# Check all time steps have values
print(f"Time range: {time_vals[0]} to {time_vals[-1]}")
print(f"Number of time steps: {len(time_vals)}")

# Check latitude and longitude coordinates
print(f"Latitude range: {ds_out.latitude.values.min():.2f} to {ds_out.latitude.values.max():.2f}")
print(f"Longitude range: {ds_out.longitude.values.min():.2f} to {ds_out.longitude.values.max():.2f}")

# Check dtype
print(f"mhw dtype: {ds_out['mhw'].dtype}")
print(f"mhw values: {np.unique(ds_out['mhw'].values)}")
