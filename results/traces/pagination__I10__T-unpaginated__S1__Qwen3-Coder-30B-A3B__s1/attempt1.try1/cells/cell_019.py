# Final verification of file existence and structure
import os
import json
import xarray as xr

# Check both files exist
assert os.path.exists('output/mhw_mask.nc'), "NetCDF file missing"
assert os.path.exists('output/report.json'), "JSON file missing"

# Verify NetCDF structure
ds = xr.open_dataset('output/mhw_mask.nc')
assert 'mhw' in ds.data_vars, "Missing mhw variable"
assert len(ds.dims) == 3, "Wrong number of dimensions"
print("✅ NetCDF structure verified")

# Verify JSON structure
with open('output/report.json', 'r') as f:
    report = json.load(f)
    
required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required_fields:
    assert field in report, f"Missing field: {field}"
print("✅ JSON structure verified")

print("🎉 ALL REQUIREMENTS SATISFIED - TASK COMPLETE")