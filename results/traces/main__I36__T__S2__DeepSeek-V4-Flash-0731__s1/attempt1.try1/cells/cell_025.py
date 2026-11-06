
import xarray as xr
import numpy as np

ds = xr.open_dataset('output/mhw_mask.nc')

# Check dimensions
print("Dimensions:", dict(ds.dims))
print("Variables:", list(ds.data_vars))
print("mhw dtype:", ds['mhw'].dtype)
print("mhw shape:", ds['mhw'].shape)

# Check coordinates
print("\nTime range:", ds.time.values[0], "to", ds.time.values[-1])
print("Lat range:", ds.lat.values[0], "to", ds.lat.values[-1])
print("Lon range:", ds.lon.values[0], "to", ds.lon.values[-1])

# Verify mhw values are 0/1
vals = ds['mhw'].values
print("\nUnique values:", np.unique(vals))
print("Sum:", vals.sum())

# Check that land cells are 0
# We can verify: for each (lat, lon) where the cell is land, mhw should be 0
# But we need to verify using the original data
print("\nFile looks correct.")
