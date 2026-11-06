
import xarray as xr
import json
import numpy as np

# Load the output
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds.mhw.values

# Check active days
active = np.any(mhw, axis=(1, 2))
print("Active days:", active.sum())
print("Active day indices:", np.where(active)[0])

# Print dates and active status
time_vals = ds.time.values
for i in range(len(time_vals)):
    if active[i]:
        print(f"  {np.datetime_as_string(time_vals[i])}: ACTIVE ({mhw[i].sum()} cells in MHW)")

# Check the event boundaries
print("\nEvent onset day (July 14):", np.datetime_as_string(time_vals[43]))
print("Day before event (July 13):", np.datetime_as_string(time_vals[42]), "active:", active[42])
print("Event end day (Aug 8):", np.datetime_as_string(time_vals[68]))
print("Day after event (Aug 9):", np.datetime_as_string(time_vals[69]), "active:", active[69])

# Verify mhw mask for land cells
print("\nLand cells (always 0 in mask):", (mhw.sum(axis=0) == 0).sum(), "out of", mhw.shape[1]*mhw.shape[2])
print("mhw sum by day (first 10):", mhw.sum(axis=(1,2))[:10])
