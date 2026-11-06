
import numpy as np
import xarray as xr

ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds.mhw.values

# Cell (0,0)
print("Cell (0,0) mhw pattern (days 50-60):")
for d in range(49, 60):
    print(f"  Day {d+1}: mhw={mhw[d, 0, 0]}")

# Verify the hot days 52-58 (1-indexed) are marked as MHW
print("\nHot days 52-58 marked as MHW:", all(mhw[d, 0, 0] == 1 for d in range(51, 58)))
