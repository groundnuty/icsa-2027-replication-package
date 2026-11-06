
import xarray as xr
import json
import numpy as np

# Verify NetCDF
ds_out = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("=== NetCDF ===")
print(ds_out)
print("\nmhw dtype:", ds_out['mhw'].dtype)
print("mhw shape:", ds_out['mhw'].shape)
print("mhw sum:", ds_out['mhw'].values.sum())
print("time range:", ds_out.time.values[0], "to", ds_out.time.values[-1])
print("lat range:", ds_out.lat.values[0], "to", ds_out.lat.values[-1])
print("lon range:", ds_out.lon.values[0], "to", ds_out.lon.values[-1])

# Verify mhw mask matches what we computed
print("\nmhw unique values:", np.unique(ds_out['mhw'].values))

# Verify report
print("\n=== Report ===")
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(json.dumps(report, indent=2))
print("\nReport keys:", sorted(report.keys()))
