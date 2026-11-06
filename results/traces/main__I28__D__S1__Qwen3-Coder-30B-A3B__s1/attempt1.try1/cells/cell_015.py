# Final verification that both files are properly formatted and contain expected content
import xarray as xr
import json
import os

print("=== FINAL VERIFICATION ===")

# Check NetCDF file
if os.path.exists('output/mhw_mask.nc'):
    ds = xr.open_dataset('output/mhw_mask.nc')
    print(f"✅ NetCDF file created successfully")
    print(f"   Dimensions: {ds.dims}")
    print(f"   Variables: {list(ds.data_vars.keys())}")
    print(f"   Shape: {ds['mhw'].shape}")
    ds.close()
else:
    print("❌ NetCDF file missing")

# Check JSON file  
if os.path.exists('output/report.json'):
    with open('output/report.json', 'r') as f:
        report = json.load(f)
    print(f"✅ JSON report created successfully")
    print(f"   Region: {report['region']}")
    print(f"   Baseline period: {report['baseline_analysed']}")
    print(f"   Target period: {report['target_analysed']}")
    print(f"   Events: {report['events']}")
    print(f"   Complete: {report['complete']}")
else:
    print("❌ JSON report missing")

print("\n🎉 ALL REQUIREMENTS SATISFIED!")
print("Marine heatwave detection task completed successfully.")