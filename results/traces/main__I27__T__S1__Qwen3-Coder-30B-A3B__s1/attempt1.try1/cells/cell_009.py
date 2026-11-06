# Final verification of output files
import os
import json

print("FINAL VERIFICATION OF OUTPUT FILES")
print("=" * 40)

# Check report.json
if os.path.exists('output/report.json'):
    print("✓ output/report.json - EXISTS")
    with open('output/report.json', 'r') as f:
        report = json.load(f)
        print(f"  Region: {report['region']}")
        print(f"  Events: {len(report['events'])} found")
        if report['events']:
            for i, event in enumerate(report['events'], 1):
                print(f"    Event {i}: {event['onset']} to {event['end']}")
else:
    print("✗ output/report.json - MISSING")

# Check mhw_mask.nc
if os.path.exists('output/mhw_mask.nc'):
    print("✓ output/mhw_mask.nc - EXISTS")
    # Try to read basic info
    try:
        import xarray as xr
        ds = xr.open_dataset('output/mhw_mask.nc')
        print(f"  Dimensions: {ds.dims}")
        print(f"  Variables: {list(ds.data_vars.keys())}")
        ds.close()
    except Exception as e:
        print(f"  Error reading NetCDF: {e}")
else:
    print("✗ output/mhw_mask.nc - MISSING")

print("\nAnalysis complete and files verified!")