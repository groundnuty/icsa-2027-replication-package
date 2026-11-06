import os
import xarray as xr
import json

# Check if output files exist
print("Checking output files...")

# Check NetCDF file
nc_file = 'output/mhw_mask.nc'
if os.path.exists(nc_file):
    print("✓ mhw_mask.nc exists")
    # Load and inspect
    try:
        ds = xr.open_dataset(nc_file)
        print(f"  Dimensions: {ds.dims}")
        print(f"  Variables: {list(ds.data_vars.keys())}")
        print(f"  Shape: {ds.mhw.shape}")
        print(f"  Time range: {ds.time.min().values} to {ds.time.max().values}")
        print(f"  Lat range: {ds.latitude.min().values} to {ds.latitude.max().values}")
        print(f"  Lon range: {ds.longitude.min().values} to {ds.longitude.max().values}")
        ds.close()
    except Exception as e:
        print(f"  Error reading NetCDF: {e}")
else:
    print("✗ mhw_mask.nc missing")

# Check JSON file
json_file = 'output/report.json'
if os.path.exists(json_file):
    print("✓ report.json exists")
    try:
        with open(json_file, 'r') as f:
            report = json.load(f)
        print(f"  Region: {report['region']}")
        print(f"  Baseline period: {report['baseline_analysed']}")
        print(f"  Target period: {report['target_analysed']}")
        print(f"  Number of events: {len(report['events'])}")
        if report['events']:
            print("  Events:")
            for event in report['events']:
                print(f"    {event['onset']} to {event['end']}")
    except Exception as e:
        print(f"  Error reading JSON: {e}")
else:
    print("✗ report.json missing")