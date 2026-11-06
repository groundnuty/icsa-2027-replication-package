
import json

with open('output/report.json', 'r') as f:
    report = json.load(f)
print(json.dumps(report, indent=2))

# Check required fields
required = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
print("\nRequired fields check:")
for field in required:
    print(f"  {field}: {'OK' if field in report else 'MISSING'}")

# Check events are in time order
events = report['events']
for i in range(len(events) - 1):
    if events[i]['onset'] >= events[i+1]['onset']:
        print(f"  Events NOT in time order at index {i}")
        break
else:
    print("  Events in time order: OK")

# Check region
expected = {"lat_min": 57.83, "lat_max": 59.03, "lon_min": 17.41, "lon_max": 18.61}
print(f"  Region matches: {report['region'] == expected}")

# Check baseline and target
print(f"  Baseline: {report['baseline_analysed']}")
print(f"  Target: {report['target_analysed']}")
print(f"  Complete: {report['complete']}")
print(f"  Caveats: '{report['caveats']}'")
