
import json

with open('output/report.json') as f:
    report = json.load(f)

print("report.json contents:")
print(json.dumps(report, indent=2))
print(f"\nFields: {list(report.keys())}")

# Check required fields
required = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required:
    assert field in report, f"Missing field: {field}"
print("All required fields present")

# Check region
assert report['region'] == {"lat_min": 60.09, "lat_max": 61.29, "lon_min": 20.01, "lon_max": 21.21}
print("Region correct")

# Check baseline
print(f"baseline_analysed: {report['baseline_analysed']}")

# Check target
print(f"target_analysed: {report['target_analysed']}")

# Check events
print(f"Events: {report['events']}")

# Check complete
print(f"complete: {report['complete']}")
