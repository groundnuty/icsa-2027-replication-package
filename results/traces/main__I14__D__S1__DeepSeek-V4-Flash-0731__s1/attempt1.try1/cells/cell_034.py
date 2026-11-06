
import xarray as xr
import json

# Check mhw_mask.nc
ds = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
print("=== mhw_mask.nc ===")
print(ds)
print(f"\nDims: {dict(ds.sizes)}")
print(f"\nmhw dtype: {ds['mhw'].dtype}")
print(f"mhw shape: {ds['mhw'].shape}")
print(f"Time values: {ds['time'].values[0]} to {ds['time'].values[-1]}")
print(f"Lat values: {ds['lat'].values[0]} to {ds['lat'].values[-1]}")
print(f"Lon values: {ds['lon'].values[0]} to {ds['lon'].values[-1]}")
print(f"Number of ones in mhw: {ds['mhw'].sum().values}")

# Check report.json
with open('/work/output/report.json', 'r') as f:
    report = json.load(f)
print("\n=== report.json ===")
print(json.dumps(report, indent=2))
