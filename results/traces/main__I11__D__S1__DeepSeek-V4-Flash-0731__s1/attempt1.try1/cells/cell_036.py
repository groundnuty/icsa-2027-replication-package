
import os
import json

# Check output files exist
print("Checking output files...")
print(f"output/mhw_mask.nc exists: {os.path.exists('output/mhw_mask.nc')}")
print(f"output/report.json exists: {os.path.exists('output/report.json')}")

# Check file sizes
mhw_size = os.path.getsize('output/mhw_mask.nc')
report_size = os.path.getsize('output/report.json')
print(f"mhw_mask.nc size: {mhw_size} bytes")
print(f"report.json size: {report_size} bytes")

# Read report
with open('output/report.json', 'r') as f:
    report = json.load(f)

print("\nReport content:")
print(json.dumps(report, indent=2))

# Verify all required fields
expected_fields = {'region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats'}
actual_fields = set(report.keys())
print(f"\nExpected fields: {expected_fields}")
print(f"Actual fields: {actual_fields}")
print(f"Fields match: {expected_fields == actual_fields}")

# Verify events format
for event in report['events']:
    assert 'onset' in event and 'end' in event
    assert isinstance(event['onset'], str) and isinstance(event['end'], str)
print(f"\nEvents format: OK ({len(report['events'])} events)")

# Verify complete
assert isinstance(report['complete'], bool)
print(f"Complete: {report['complete']} (type: {type(report['complete']).__name__})")

# Verify caveats is a string
assert isinstance(report['caveats'], str)
print(f"Caveats: '{report['caveats']}'")

print("\nAll checks passed!")
