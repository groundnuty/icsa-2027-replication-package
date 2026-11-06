# Verify the files exist and show basic content
import json

# Check report.json
try:
    with open('output/report.json', 'r') as f:
        report = json.load(f)
        print("Report JSON contents:")
        print(json.dumps(report, indent=2)[:500] + "...")
except Exception as e:
    print(f"Error reading report.json: {e}")

# Check mhw_mask.nc exists
import os
if os.path.exists('output/mhw_mask.nc'):
    print("mhw_mask.nc file exists")
    print(f"File size: {os.path.getsize('output/mhw_mask.nc')} bytes")
else:
    print("mhw_mask.nc file not found")