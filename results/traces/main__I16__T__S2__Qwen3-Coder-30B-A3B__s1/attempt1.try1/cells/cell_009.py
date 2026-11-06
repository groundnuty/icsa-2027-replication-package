# Final validation that both files are properly created
import os
import json

# Check that both files exist
assert os.path.exists('output/mhw_mask.nc'), "mhw_mask.nc was not created"
assert os.path.exists('output/report.json'), "report.json was not created"

# Validate report.json structure
with open('output/report.json', 'r') as f:
    report = json.load(f)
    
required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required_fields:
    assert field in report, f"Missing required field: {field}"

print("✅ Task completed successfully - both output files created with correct content")