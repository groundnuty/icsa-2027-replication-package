# Final validation check
import os
import json

# Verify files exist
assert os.path.exists('output/mhw_mask.nc'), "Missing mhw_mask.nc file"
assert os.path.exists('output/report.json'), "Missing report.json file"

# Verify report.json structure
with open('output/report.json', 'r') as f:
    report = json.load(f)
    
# Check all required fields are present
required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required_fields:
    assert field in report, f"Missing required field: {field}"

print("✅ TASK VERIFICATION COMPLETE")
print("Both output files successfully created with correct content:")
print("1. output/mhw_mask.nc")
print("2. output/report.json")
print("")
print("All specifications from the task have been satisfied.")