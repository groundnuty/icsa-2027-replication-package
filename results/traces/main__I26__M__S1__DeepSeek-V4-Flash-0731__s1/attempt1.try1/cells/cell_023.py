
import xarray as xr
import json

# Verify the NetCDF file
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("Dataset info:")
print(ds)
print(f"\nmhw dtype: {ds['mhw'].dtype}")
print(f"mhw shape: {ds['mhw'].shape}")
print(f"mhw values: {ds['mhw'].values.min()} to {ds['mhw'].values.max()}")
print(f"mhw sum: {ds['mhw'].values.sum()}")
print(f"Time range: {ds['time'].values[0]} to {ds['time'].values[-1]}")
print(f"Lat range: {ds['lat'].values[0]} to {ds['lat'].values[-1]}")
print(f"Lon range: {ds['lon'].values[0]} to {ds['lon'].values[-1]}")
ds.close()

# Verify report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(f"\nReport:")
print(json.dumps(report, indent=2))
