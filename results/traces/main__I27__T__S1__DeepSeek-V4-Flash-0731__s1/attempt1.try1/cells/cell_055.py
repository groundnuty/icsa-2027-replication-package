
import xarray as xr
import numpy as np

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc')
print("Dataset structure:")
print(ds)
print()

# Check the mhw variable
print("mhw dtype:", ds.mhw.dtype)
print("mhw shape:", ds.mhw.shape)
print("mhw unique:", np.unique(ds.mhw.values))
print("mhw sum:", int(ds.mhw.values.sum()))
print()

# Check coordinates
print("Time values:", ds.time.values[:3], "...", ds.time.values[-3:])
print("Lat values:", ds.lat.values[:3], "...", ds.lat.values[-3:], f"(n={len(ds.lat)})")
print("Lon values:", ds.lon.values[:3], "...", ds.lon.values[-3:], f"(n={len(ds.lon)})")
print()

# Check some specific values
# Count sea cells with MHW on each day
mhw_per_day = ds.mhw.values.sum(axis=(1, 2))
print("MHW cells per day:")
for i in range(len(ds.time)):
    if mhw_per_day[i] > 0:
        print(f"  {str(ds.time.values[i])[:10]}: {int(mhw_per_day[i])} cells")
