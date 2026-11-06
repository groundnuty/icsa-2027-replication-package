# Final verification that files were created correctly
import os
import json

# Verify output files exist
assert os.path.exists('output/mhw_mask.nc'), "mhw_mask.nc not created"
assert os.path.exists('output/report.json'), "report.json not created"

# Read and validate report
with open('output/report.json', 'r') as f:
    report = json.load(f)
    
# Validate required fields
required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required_fields:
    assert field in report, f"Missing required field: {field}"

print("✅ All checks passed - analysis completed successfully")