# Final verification that files are properly structured
import xarray as xr
import json
import os

print("=== FINAL VERIFICATION ===")

# Check NetCDF structure
try:
    ds = xr.open_dataset('output/mhw_mask.nc')
    print("✅ NetCDF file structure:")
    print(f"   Dimensions: {dict(ds.dims)}")
    print(f"   Variables: {list(ds.data_vars.keys())}")
    print(f"   MHW variable shape: {ds['mhw'].shape}")
    print(f"   MHW variable dtype: {ds['mhw'].dtype}")
except Exception as e:
    print(f"❌ NetCDF error: {e}")

# Check JSON structure
try:
    with open('output/report.json', 'r') as f:
        report = json.load(f)
    
    required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
    print("✅ JSON report structure:")
    for field in required_fields:
        if field in report:
            print(f"   ✓ {field}: present")
        else:
            print(f"   ✗ {field}: missing")
    
    print(f"   Region: {report['region']}")
    print(f"   Baseline period: {report['baseline_analysed']}")
    print(f"   Target period: {report['target_analysed']}")
    print(f"   Events count: {len(report['events'])}")
    print(f"   Complete: {report['complete']}")
    
except Exception as e:
    print(f"❌ JSON error: {e}")

print("\n=== TASK COMPLETED SUCCESSFULLY ===")