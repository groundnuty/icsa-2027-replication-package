
import os

# Check files exist
print("Files in output/:")
for f in os.listdir('output'):
    print(f"  {f}: {os.path.getsize(os.path.join('output', f))} bytes")

# Final verification of report.json content
import json
with open('output/report.json', 'r') as f:
    report = json.load(f)
    
# Verify exact fields
expected_keys = {'region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats'}
actual_keys = set(report.keys())
print("\nReport keys:", actual_keys)
print("All expected keys present:", expected_keys == actual_keys)

# Verify region
assert report['region'] == {"lat_min": 64.39, "lat_max": 65.59, "lon_min": 23.41, "lon_max": 24.61}

# Verify baseline
assert report['baseline_analysed'] == {"start": "1991-12-27", "end": "2003-01-05"}

# Verify target
assert report['target_analysed'] == {"start": "2013-06-01", "end": "2013-08-31"}

# Verify events
assert report['events'] == [{"onset": "2013-06-01", "end": "2013-07-01"}]

# Verify complete and caveats
assert report['complete'] == True
assert report['caveats'] == ""

print("\nAll assertions passed!")
