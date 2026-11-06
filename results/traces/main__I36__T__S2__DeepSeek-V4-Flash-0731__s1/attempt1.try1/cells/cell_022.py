
import xarray as xr
import json

# Verify the NetCDF file
ds = xr.open_dataset('output/mhw_mask.nc')
print(ds)
print(f"mhw dtype: {ds['mhw'].dtype}")
print(f"mhw shape: {ds['mhw'].shape}")
print(f"mhw min: {ds['mhw'].min().values}, max: {ds['mhw'].max().values}")
print(f"mhw sum: {ds['mhw'].sum().values}")
print(f"Time range: {ds.time.values[0]} to {ds.time.values[-1]}")
print(f"Lat range: {ds.latitude.values[0]} to {ds.latitude.values[-1]}")
print(f"Lon range: {ds.longitude.values[0]} to {ds.longitude.values[-1]}")

# Verify the report
with open('output/report.json', 'r') as f:
    report = json.load(f)
print("\nReport:")
print(json.dumps(report, indent=2))
