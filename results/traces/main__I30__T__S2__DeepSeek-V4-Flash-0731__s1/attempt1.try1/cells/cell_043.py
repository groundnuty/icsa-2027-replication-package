
import xarray as xr
import numpy as np

# Verify NetCDF
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("Dataset:")
print(ds)
print()

# Check mhw values
mhw = ds['mhw'].values
print("mhw dtype:", mhw.dtype)
print("mhw shape:", mhw.shape)
print("mhw min:", mhw.min(), "max:", mhw.max())
print("mhw sum:", mhw.sum())

# Check coordinates
print("\ntime:", ds['time'].values[0], "to", ds['time'].values[-1], "count:", len(ds['time']))
print("lat:", ds['latitude'].values[0], "to", ds['latitude'].values[-1], "count:", len(ds['latitude']))
print("lon:", ds['longitude'].values[0], "to", ds['longitude'].values[-1], "count:", len(ds['longitude']))

# Verify mhw values match what we computed
mhw_mask = np.load('/tmp/mhw_mask.npy')
expected = mhw_mask.astype(np.uint8)
print("\nmhw matches expected:", np.array_equal(mhw, expected))

# Check that land cells are 0
sea_mask = np.load('/tmp/sea_mask.npy')
land_cells = ~sea_mask
print("Land cells in mhw (should be 0):", mhw[:, land_cells].max())

ds.close()
