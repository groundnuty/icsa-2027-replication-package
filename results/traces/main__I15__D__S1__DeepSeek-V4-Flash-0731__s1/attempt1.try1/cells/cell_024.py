
import xarray as xr
import json
import numpy as np

# Verify NetCDF
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("NetCDF file:")
print(ds)
print("mhw dtype:", ds.mhw.dtype)
print("mhw shape:", ds.mhw.shape)
print("mhw values range:", ds.mhw.min().values, "-", ds.mhw.max().values)
print("time range:", ds.time.values[0], "to", ds.time.values[-1])
print("time count:", len(ds.time))
print("lat range:", ds.lat.values[0], "to", ds.lat.values[-1])
print("lon range:", ds.lon.values[0], "to", ds.lon.values[-1])

# Count MHW days
mhw = ds.mhw.values
print("Total MHW cell-days:", np.sum(mhw))
print("Active days:", np.sum(np.any(mhw > 0, axis=(1,2))))

# Verify report
with open('output/report.json') as f:
    report = json.load(f)
print("\nReport:")
print(json.dumps(report, indent=2))
