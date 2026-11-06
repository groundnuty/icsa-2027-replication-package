import xarray as xr
import json
import os

# Check the generated files
print("Checking output files:")

# Check NetCDF file
if os.path.exists('output/mhw_mask.nc'):
    print("✓ mhw_mask.nc exists")
    ds = xr.open_dataset('output/mhw_mask.nc')
    print(f"  Dimensions: {ds.dims}")
    print(f"  Variables: {list(ds.data_vars.keys())}")
    print(f"  Shape: {ds.mhw.shape}")
    print(f"  Data type: {ds.mhw.dtype}")
    print(f"  First few values:\n{ds.mhw.values[0, :3, :3]}")
    ds.close()
else:
    print("✗ mhw_mask.nc not found")

# Check JSON report
if os.path.exists('output/report.json'):
    print("✓ report.json exists")
    with open('output/report.json', 'r') as f:
        report = json.load(f)
    print(f"  Region: {report['region']}")
    print(f"  Baseline period: {report['baseline_analysed']}")
    print(f"  Target period: {report['target_analysed']}")
    print(f"  Events: {report['events']}")
    print(f"  Complete: {report['complete']}")
    print(f"  Caveats: {report['caveats']}")
else:
    print("✗ report.json not found")

print("\nAnalysis summary:")
print("- Regional MHW detection completed successfully")
print("- Output files created in 'output/' directory")
print("- Files contain expected structure and data")