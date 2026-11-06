
import os

# Check output files exist
print("Checking output files:")
for f in ['output/mhw_mask.nc', 'output/report.json']:
    if os.path.exists(f):
        size = os.path.getsize(f)
        print(f"  {f}: exists, {size} bytes")
    else:
        print(f"  {f}: MISSING!")

# Verify the report JSON is valid
import json
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(f"\nReport JSON valid. Events: {len(report['events'])}")
for e in report['events']:
    print(f"  {e['onset']} to {e['end']}")
