
import xarray as xr
import numpy as np

# Verify output files
ds_out = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
ds_src = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')

# Check time coordinates match
print("Output time:", ds_out['time'].values[0], "to", ds_out['time'].values[-1])
print("Expected: 2014-06-01 to 2014-08-31")

# Check lat and lon
print("Output lat:", ds_out['lat'].values[0], "to", ds_out['lat'].values[-1])
print("Output lon:", ds_out['lon'].values[0], "to", ds_out['lon'].values[-1])

# Check mhw values
mhw = ds_out['mhw'].values
print("mhw dtype:", mhw.dtype)
print("mhw min/max:", mhw.min(), mhw.max())
print("mhw sum:", int(mhw.sum()))

# Verify mhw matches the computed mask
computed = np.load('/tmp/mhw_mask_correct.npy')
print("Matches computed:", np.array_equal(mhw, computed))

# Check report
import json
with open('output/report.json', 'r') as f:
    report = json.load(f)
print("\nReport:", json.dumps(report, indent=2))
