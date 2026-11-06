import os
import json
import xarray as xr

# Check if output files exist
print("Checking output files:")

# Check mhw_mask.nc
if os.path.exists('output/mhw_mask.nc'):
    print("✓ mhw_mask.nc exists")
    # Load and inspect the file
    ds = xr.open_dataset('output/mhw_mask.nc')
    print(f"  Dimensions: {ds.dims}")
    print(f"  Variables: {list(ds.data_vars.keys())}")
    print(f"  Shape: {ds.mhw.shape}")
else:
    print("✗ mhw_mask.nc missing")

# Check report.json
if os.path.exists('output/report.json'):
    print("✓ report.json exists")
    with open('output/report.json', 'r') as f:
        report = json.load(f)
    print(f"  Region: {report['region']}")
    print(f"  Baseline period: {report['baseline_analysed']}")
    print(f"  Target period: {report['target_analysed']}")
    print(f"  Number of events: {len(report['events'])}")
    if report['events']:
        print("  Events:")
        for event in report['events']:
            print(f"    {event['onset']} to {event['end']}")
else:
    print("✗ report.json missing")

print("\nAnalysis complete!")