
import xarray as xr
import json
import numpy as np

# Check mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("mhw values unique:", set(np.unique(ds.mhw.values)))
print("mhw sum:", int(ds.mhw.values.sum()))

# Check report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)
print("\nreport.json:")
print(json.dumps(report, indent=2))
