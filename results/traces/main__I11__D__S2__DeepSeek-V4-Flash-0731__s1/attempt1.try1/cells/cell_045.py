
import numpy as np
import xarray as xr

ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds.mhw.values
cell = mhw[:, 4, 51].astype(bool)

# Check days 17-57 (inclusive)
joined = cell[17:58]
print(f"Days 17-57 all MHW: {np.all(joined)}")
print(f"Days 12-16 all not MHW: {not np.any(cell[12:17])}")

# Verify the joined MHW covers the gap day (day 51)
print(f"Day 51 (gap day): MHW={cell[51]}")
print(f"Day 52 (start of MHW2): MHW={cell[52]}")
print(f"Day 50 (end of MHW1): MHW={cell[50]}")
