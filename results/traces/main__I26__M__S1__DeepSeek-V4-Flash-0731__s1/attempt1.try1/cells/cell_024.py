
import json

with open('output/report.json', 'r') as f:
    report = json.load(f)

# Check required fields
required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required_fields:
    if field in report:
        print(f"✓ {field}: {report[field]}")
    else:
        print(f"✗ Missing field: {field}")

# Check region format
region = report['region']
print(f"\nRegion: lat [{region['lat_min']}, {region['lat_max']}], lon [{region['lon_min']}, {region['lon_max']}]")

# Check events format
print(f"\nEvents ({len(report['events'])}):")
for ev in report['events']:
    print(f"  onset={ev['onset']}, end={ev['end']}")
