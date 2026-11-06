import xarray as xr
import numpy as np

ds_out = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds_out['mhw'].values
daily = mhw.sum(axis=(1,2))

# Print daily active for days 10-40 (0-indexed: day 10 = June 11)
for t in range(92):
    date_str = str(ds_out['time'].values[t])[:10]
    if daily[t] > 0:
        print(f"  {date_str}: {daily[t]} active cells")
