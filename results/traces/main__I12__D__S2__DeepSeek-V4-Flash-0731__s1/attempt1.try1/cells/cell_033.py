
import json

with open('output/report.json') as f:
    report = json.load(f)

print(json.dumps(report, indent=2, default=str))

# Verify all required fields are present
required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required_fields:
    assert field in report, f"Missing field: {field}"
print("\nAll required fields present ✓")

# Verify region
assert report['region'] == {'lat_min': 56.09, 'lat_max': 57.29, 'lon_min': 10.55, 'lon_max': 11.75}
print("Region correct ✓")

# Verify baseline
assert report['baseline_analysed'] == {'start': '1991-12-27', 'end': '2003-01-05'}
print("Baseline correct ✓")

# Verify target
assert report['target_analysed'] == {'start': '2009-06-01', 'end': '2009-08-31'}
print("Target correct ✓")

# Verify events
print(f"Events: {report['events']}")
for ev in report['events']:
    assert 'onset' in ev and 'end' in ev
print("Events format correct ✓")

# Verify complete
assert report['complete'] == True
print("Complete flag correct ✓")

# Verify caveats is a string
assert isinstance(report['caveats'], str)
print("Caveats is string ✓")
