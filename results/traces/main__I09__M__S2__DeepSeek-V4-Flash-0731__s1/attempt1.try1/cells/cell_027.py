
import xarray as xr
import numpy as np

# Read back the netCDF file
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(ds)
print()

# Check dimensions
print("Dimensions:", dict(ds.sizes))
print()

# Check mhw variable
print("mhw dtype:", ds['mhw'].dtype)
print("mhw shape:", ds['mhw'].shape)
print("mhw min:", ds['mhw'].min().values)
print("mhw max:", ds['mhw'].max().values)
print("mhw sum:", ds['mhw'].sum().values)
print()

# Check coordinates
print("Time range:", ds['time'].values[0], "to", ds['time'].values[-1])
print("Lat range:", ds['lat'].values[0], "to", ds['lat'].values[-1])
print("Lon range:", ds['lon'].values[0], "to", ds['lon'].values[-1])

# Check some values
print("\nSample mhw values:")
print("Cell (30,30) time series:", ds['mhw'][:, 30, 30].values)

# Verify land cells are 0
sea_mask = np.load('/tmp/sea_mask.npy')
land_cells = ~sea_mask
land_sum = np.sum(ds['mhw'].values[:, land_cells])
print(f"Land cell mhw sum: {land_sum} (should be 0)")

# Verify the time dimension has 92 entries
print(f"Time dimension size: {len(ds['time'])}")

ds.close()
