
import xarray as xr
import numpy as np
import json

# Final verification
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("=== mhw_mask.nc ===")
print(f"Dimensions: {dict(ds.sizes)}")
print(f"Variables: {list(ds.data_vars)}")
print(f"mhw dtype: {ds.mhw.dtype}")
print(f"mhw values: {np.unique(ds.mhw.values)}")
print(f"Time: {ds.time.values[0]} to {ds.time.values[-1]}, count={len(ds.time)}")
print(f"Lat: {ds.lat.values[0]} to {ds.lat.values[-1]}, count={len(ds.lat)}")
print(f"Lon: {ds.lon.values[0]} to {ds.lon.values[-1]}, count={len(ds.lon)}")

print("\n=== report.json ===")
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(f"Keys: {list(report.keys())}")
print(f"region: {report['region']}")
print(f"baseline_analysed: {report['baseline_analysed']}")
print(f"target_analysed: {report['target_analysed']}")
print(f"events: {report['events']}")
print(f"complete: {report['complete']}")
print(f"caveats: {report['caveats']}")
