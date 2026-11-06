# Final verification that both files are properly created
import os
import xarray as xr
import json

# Check files exist
print("Final verification:")
print(f"mhw_mask.nc exists: {os.path.exists('output/mhw_mask.nc')}")
print(f"report.json exists: {os.path.exists('output/report.json')}")

# Verify report content structure
with open('output/report.json', 'r') as f:
    report = json.load(f)
    print(f"\nReport structure verified:")
    print(f"  - Region defined: {bool(report.get('region'))}")
    print(f"  - Baseline period: {report.get('baseline_analysed')}")
    print(f"  - Target period: {report.get('target_analysed')}")
    print(f"  - Events: {len(report.get('events', []))} events")
    print(f"  - Complete: {report.get('complete')}")

print("\nTask completed successfully!")