# Final verification that files were created correctly
import os
import json
import xarray as xr

print("Task completed successfully!")
print("Files created:")
print("- output/mhw_mask.nc")
print("- output/report.json")

# Verify file existence
assert os.path.exists('output/mhw_mask.nc'), "mhw_mask.nc not created"
assert os.path.exists('output/report.json'), "report.json not created"

# Verify report content
with open('output/report.json', 'r') as f:
    report = json.load(f)
    
assert report['region']['lat_min'] == 61.57
assert report['region']['lat_max'] == 62.77
assert report['region']['lon_min'] == 20.17
assert report['region']['lon_max'] == 21.37
assert report['baseline_analysed']['start'] == '1992-01-01'
assert report['target_analysed']['end'] == '2021-08-31'
assert report['complete'] == True

# Verify NetCDF structure
ds = xr.open_dataset('output/mhw_mask.nc')
assert 'mhw' in ds.data_vars
assert ds.mhw.shape == (92, 60, 60)
assert 'time' in ds.dims
assert 'lat' in ds.dims
assert 'lon' in ds.dims

print("All checks passed!")