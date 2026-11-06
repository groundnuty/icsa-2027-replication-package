
import os
import json

# Check output files exist
print("Output directory contents:")
for f in sorted(os.listdir('output')):
    path = os.path.join('output', f)
    size = os.path.getsize(path)
    print(f"  {f}: {size} bytes")

# Verify report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)
print("\nReport contents:")
print(json.dumps(report, indent=2))

# Verify report has exactly the right fields
expected_fields = set(['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats'])
actual_fields = set(report.keys())
print(f"\nExpected fields: {expected_fields}")
print(f"Actual fields: {actual_fields}")
print(f"Match: {expected_fields == actual_fields}")
