import xarray as xr
import json

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("=== mhw_mask.nc ===")
print(ds)
print(f"\nmhw dtype: {ds['mhw'].dtype}")
print(f"mhw dims: {dict(ds['mhw'].sizes)}")
print(f"time range: {ds.time.values[0]} to {ds.time.values[-1]}")
print(f"time count: {len(ds.time.values)}")
print(f"lat range: {ds.lat.values[0]} to {ds.lat.values[-1]}")
print(f"lon range: {ds.lon.values[0]} to {ds.lon.values[-1]}")
print(f"mhw values: min={ds['mhw'].min().values}, max={ds['mhw'].max().values}")
print(f"mhw sum: {ds['mhw'].sum().values}")
ds.close()

print("\n=== report.json ===")
with open('output/report.json') as f:
    report = json.load(f)
print(json.dumps(report, indent=2))
