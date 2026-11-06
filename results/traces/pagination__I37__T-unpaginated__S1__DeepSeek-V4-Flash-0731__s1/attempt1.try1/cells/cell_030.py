
import xarray as xr
import numpy as np

# Read back the output file
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(ds)
print(f"\nDims: {dict(ds.sizes)}")
print(f"mhw dtype: {ds.mhw.dtype}")
print(f"mhw min/max: {ds.mhw.min().values}, {ds.mhw.max().values}")
print(f"mhw sum: {ds.mhw.sum().values}")
print(f"time: {ds.time.values[:3]} ... {ds.time.values[-3:]}")
print(f"lat: {ds.lat.values[:3]} ... {ds.lat.values[-3:]}")
print(f"lon: {ds.lon.values[:3]} ... {ds.lon.values[-3:]}")
ds.close()

# Read back the report
import json
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(f"\nReport: {json.dumps(report, indent=2)}")
