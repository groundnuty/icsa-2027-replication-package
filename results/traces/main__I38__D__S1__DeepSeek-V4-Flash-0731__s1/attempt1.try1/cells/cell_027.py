
import os
print("Current working directory:", os.getcwd())
print("output exists:", os.path.exists('output'))
print("mhw_mask.nc exists:", os.path.exists('output/mhw_mask.nc'))
print("report.json exists:", os.path.exists('output/report.json'))
print("\nFiles in output:")
for f in os.listdir('output'):
    print(f"  {f}: {os.path.getsize(os.path.join('output', f))} bytes")

# Verify report.json has exactly the required fields
import json
with open('output/report.json') as f:
    report = json.load(f)
required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
print("\nReport fields:", list(report.keys()))
print("All required fields present:", all(f in report for f in required_fields))
print("Exactly required fields:", set(report.keys()) == set(required_fields))
