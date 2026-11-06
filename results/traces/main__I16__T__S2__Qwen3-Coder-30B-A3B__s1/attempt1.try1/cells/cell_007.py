# Final verification that both files exist and are properly formatted
import os
import json

# Verify both output files exist
assert os.path.exists('output/report.json'), "report.json not created"
assert os.path.exists('output/mhw_mask.nc'), "mhw_mask.nc not created"

# Read and verify report.json content
with open('output/report.json', 'r') as f:
    report = json.load(f)
    
# Verify required fields are present
required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required_fields:
    assert field in report, f"Missing field: {field}"

# Verify region specification
region = report['region']
assert 'lat_min' in region and 'lat_max' in region and 'lon_min' in region and 'lon_max' in region

# Verify periods
baseline = report['baseline_analysed']
target = report['target_analysed']
assert 'start' in baseline and 'end' in baseline
assert 'start' in target and 'end' in target

print("✅ All checks passed - both output files created successfully with correct format")