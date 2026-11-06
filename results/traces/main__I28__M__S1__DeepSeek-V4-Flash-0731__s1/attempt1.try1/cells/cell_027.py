
import xarray as xr
import numpy as np

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("Dataset:")
print(ds)
print("\nVariable mhw shape:", ds['mhw'].shape)
print("dtype:", ds['mhw'].dtype)
print("Time:", ds['time'].values[:5], "...", ds['time'].values[-3:])
print("Lat range:", ds['lat'].values[0], "to", ds['lat'].values[-1])
print("Lon range:", ds['lon'].values[0], "to", ds['lon'].values[-1])
print("\nUnique values in mhw:", np.unique(ds['mhw'].values))
print("Sum of mhw:", np.sum(ds['mhw'].values))
ds.close()

# Verify report.json
import json
with open('output/report.json', 'r') as f:
    report = json.load(f)
print("\nReport:")
print(json.dumps(report, indent=2))

# Check that all required fields are present
required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required_fields:
    if field not in report:
        print(f"MISSING FIELD: {field}")
    else:
        print(f"Field '{field}' present: OK")
