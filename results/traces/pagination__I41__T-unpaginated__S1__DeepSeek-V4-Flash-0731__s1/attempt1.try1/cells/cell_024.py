
import os

# Check files exist
print("output/ exists:", os.path.isdir('output'))
print("output/mhw_mask.nc exists:", os.path.isfile('output/mhw_mask.nc'))
print("output/report.json exists:", os.path.isfile('output/report.json'))

# File sizes
print("\nFile sizes:")
for f in ['output/mhw_mask.nc', 'output/report.json']:
    size = os.path.getsize(f)
    print(f"  {f}: {size} bytes")

# Verify report.json is valid JSON
import json
with open('output/report.json', 'r') as f:
    report = json.load(f)

# Check all required fields
required = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required:
    print(f"  {field}: {'OK' if field in report else 'MISSING'}")

# Verify region fields
for field in ['lat_min', 'lat_max', 'lon_min', 'lon_max']:
    print(f"  region.{field}: {report['region'][field]}")

# Verify events format
for ev in report['events']:
    assert 'onset' in ev and 'end' in ev
    print(f"  event: onset={ev['onset']}, end={ev['end']}")

print(f"  complete: {report['complete']}")
print(f"  caveats: '{report['caveats']}'")
