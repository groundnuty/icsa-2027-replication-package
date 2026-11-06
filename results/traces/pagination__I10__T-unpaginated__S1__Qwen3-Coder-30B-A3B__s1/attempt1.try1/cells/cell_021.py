# Final verification that both files exist and are properly formatted
import os
import json
import xarray as xr

# Check file existence
assert os.path.exists('output/mhw_mask.nc'), "NetCDF file not found"
assert os.path.exists('output/report.json'), "JSON file not found"

# Verify NetCDF structure
ds = xr.open_dataset('output/mhw_mask.nc')
assert 'mhw' in ds.data_vars, "Missing mhw variable"
assert 'time' in ds.dims and 'lat' in ds.dims and 'lon' in ds.dims, "Missing dimensions"

# Verify JSON structure
with open('output/report.json', 'r') as f:
    report = json.load(f)
    
required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required_fields:
    assert field in report, f"Missing required field: {field}"

print("SUCCESS: All files generated and verified correctly")
print(f"NetCDF dimensions: {ds.dims}")
print(f"JSON fields present: {len(required_fields)}")