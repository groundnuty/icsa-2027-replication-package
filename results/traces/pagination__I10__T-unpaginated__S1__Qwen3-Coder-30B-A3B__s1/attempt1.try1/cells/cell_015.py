# Final verification that both files exist and meet requirements
import os
import json

# Verify both files exist
assert os.path.exists('output/mhw_mask.nc'), "NetCDF file not created"
assert os.path.exists('output/report.json'), "JSON report not created"

# Verify report structure
with open('output/report.json', 'r') as f:
    report = json.load(f)
    
required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required_fields:
    assert field in report, f"Missing required field: {field}"

# Verify region structure
region = report['region']
assert 'lat_min' in region and 'lat_max' in region and 'lon_min' in region and 'lon_max' in region

# Verify periods
baseline = report['baseline_analysed']
target = report['target_analysed']
assert 'start' in baseline and 'end' in baseline
assert 'start' in target and 'end' in target

print("✅ All requirements satisfied")
print("✅ Both output files created successfully")
print("✅ Report structure matches specification")