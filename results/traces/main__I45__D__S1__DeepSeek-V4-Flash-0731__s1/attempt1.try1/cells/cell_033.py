
import json

with open('output/report.json', 'r') as f:
    report = json.load(f)

print(json.dumps(report, indent=2))

# Verify all required fields are present
required = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required:
    assert field in report, f"Missing field: {field}"
print("\nAll required fields present.")

# Verify region
assert report['region'] == {"lat_min": 63.31, "lat_max": 64.51, "lon_min": 21.31, "lon_max": 22.51}
print("Region correct.")

# Verify baseline
assert report['baseline_analysed'] == {"start": "1991-12-27", "end": "2003-01-05"}
print("Baseline correct.")

# Verify target
assert report['target_analysed'] == {"start": "2009-06-01", "end": "2009-08-31"}
print("Target correct.")

# Verify events
expected_events = [
    {"onset": "2009-06-24", "end": "2009-07-04"},
    {"onset": "2009-08-02", "end": "2009-08-14"}
]
assert report['events'] == expected_events, f"Events mismatch: {report['events']}"
print("Events correct.")

# Verify complete
assert report['complete'] == True
print("Complete flag correct.")

print("\nAll checks passed!")
