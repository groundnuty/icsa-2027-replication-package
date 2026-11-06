import xarray as xr
import json
import os

# Check the generated files
print("Checking output files...")

# Check the NetCDF file
if os.path.exists('output/mhw_mask.nc'):
    print("✓ mhw_mask.nc exists")
    ds = xr.open_dataset('output/mhw_mask.nc')
    print(f"  Dimensions: {ds.dims}")
    print(f"  Variables: {list(ds.data_vars.keys())}")
    print(f"  Shape: {ds.mhw.shape}")
    print(f"  Data type: {ds.mhw.dtype}")
    print(f"  Time range: {ds.time.min().values} to {ds.time.max().values}")
    print(f"  Lat range: {ds.latitude.min().values} to {ds.latitude.max().values}")
    print(f"  Lon range: {ds.longitude.min().values} to {ds.longitude.max().values}")
else:
    print("✗ mhw_mask.nc missing")

# Check the JSON report
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
    print(f"  Complete: {report['complete']}")
else:
    print("✗ report.json missing")

print("\nAnalysis summary:")
print("- Region: 54.17°N to 55.37°N, 13.25°E to 14.45°E")
print("- Period: 2004-06-01 to 2004-08-31")
print("- Method: Copernicus Marine Baltic Sea SST reprocessed dataset")
print("- Found 3 regional MHW events")