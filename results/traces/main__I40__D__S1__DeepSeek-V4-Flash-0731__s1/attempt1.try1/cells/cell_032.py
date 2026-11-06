
import numpy as np
import xarray as xr

ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds.mhw.values

# Check active days for both events
for t in range(92):
    n_active = mhw[t].sum()
    if n_active > 0:
        print(f"Day {t} ({ds.time.values[t]}): {n_active} active cells")

print(f"\nTotal active cell-days: {mhw.sum()}")
