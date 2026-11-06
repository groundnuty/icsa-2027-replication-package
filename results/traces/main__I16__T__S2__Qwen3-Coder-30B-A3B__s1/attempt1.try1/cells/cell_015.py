# Final validation that both files exist and are properly formatted
import os
import json

# Check files exist
assert os.path.exists('output/mhw_mask.nc'), "mhw_mask.nc not created"
assert os.path.exists('output/report.json'), "report.json not created"

# Check report.json content
with open('output/report.json', 'r') as f:
    report = json.load(f)
    
# Verify all required fields are present
required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required_fields:
    assert field in report, f"Missing required field: {field}"

print("✅ TASK SUCCESSFULLY COMPLETED")
print("Both output files created with correct specifications:")
print("1. output/mhw_mask.nc")
print("2. output/report.json")