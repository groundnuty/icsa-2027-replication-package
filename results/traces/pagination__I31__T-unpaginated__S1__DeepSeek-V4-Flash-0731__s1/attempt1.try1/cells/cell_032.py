
import json
import numpy as np
import xarray as xr

# Check output files
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("mhw_mask.nc:")
print(ds)
print(f"mhw values: {np.unique(ds.mhw.values)}")
print(f"mhw sum: {ds.mhw.values.sum()}")
print(f"mhw shape: {ds.mhw.shape}")
print(f"time dim: {len(ds.time)}")
print(f"lat: {ds.lat.values[:5]}...{ds.lat.values[-5:]}")
print(f"lon: {ds.lon.values[:5]}...{ds.lon.values[-5:]}")

with open('output/report.json') as f:
    report = json.load(f)
print("\nreport.json:")
print(json.dumps(report, indent=2))
