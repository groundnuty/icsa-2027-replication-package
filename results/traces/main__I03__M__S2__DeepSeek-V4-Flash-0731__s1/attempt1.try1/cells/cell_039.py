
import xarray as xr
import json
import numpy as np

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("=== mhw_mask.nc ===")
print("Variables:", list(ds.data_vars))
print("mhw dtype:", ds['mhw'].dtype)
print("mhw shape:", ds['mhw'].shape)
print("dims:", dict(ds.dims))
print("time:", ds['time'].values[0], "to", ds['time'].values[-1], "count:", len(ds['time']))
print("lat:", ds['lat'].values[0], "to", ds['lat'].values[-1], "count:", len(ds['lat']))
print("lon:", ds['lon'].values[0], "to", ds['lon'].values[-1], "count:", len(ds['lon']))
print("mhw unique values:", np.unique(ds['mhw'].values))
print("mhw sum:", int(ds['mhw'].sum()))

# Verify report.json
print("\n=== report.json ===")
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(json.dumps(report, indent=2))
print("\nFields:", sorted(report.keys()))
