
import xarray as xr
import json

ds = xr.open_dataset('output/mhw_mask.nc')
print(ds)
print(f"mhw dtype: {ds['mhw'].dtype}")
print(f"Time range: {ds.time.values[0]} to {ds.time.values[-1]}")
print(f"Lat range: {ds.lat.values[0]} to {ds.lat.values[-1]}")
print(f"Lon range: {ds.lon.values[0]} to {ds.lon.values[-1]}")

with open('output/report.json', 'r') as f:
    report = json.load(f)
print("\nReport:")
print(json.dumps(report, indent=2))
