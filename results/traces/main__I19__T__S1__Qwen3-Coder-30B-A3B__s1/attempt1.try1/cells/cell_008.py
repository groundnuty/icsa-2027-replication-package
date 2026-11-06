# Verify the final state of output files
import os
import json

# Check that both files were created
assert os.path.exists('output/mhw_mask.nc'), "mhw_mask.nc was not created"
assert os.path.exists('output/report.json'), "report.json was not created"

# Read and verify the report content
with open('output/report.json', 'r') as f:
    report = json.load(f)

print("Final verification:")
print(f"Region: {report['region']}")
print(f"Baseline period: {report['baseline_analysed']}")
print(f"Target period: {report['target_analysed']}")
print(f"Number of events detected: {len(report['events'])}")
print(f"Analysis complete: {report['complete']}")

print("\nBoth required output files have been successfully created!")