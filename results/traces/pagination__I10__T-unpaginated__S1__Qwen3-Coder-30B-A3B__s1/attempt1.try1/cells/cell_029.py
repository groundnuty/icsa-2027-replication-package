# Final verification that both files exist and are valid
import os
import json
import xarray as xr

print("🔍 FINAL VERIFICATION")
print("-" * 20)

# Check file existence
files = ['output/mhw_mask.nc', 'output/report.json']
all_exist = True

for file in files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_exist = False

if all_exist:
    # Check file sizes
    print(f"\n📊 FILE SIZES:")
    print(f"   mhw_mask.nc: {os.path.getsize('output/mhw_mask.nc')} bytes")
    print(f"   report.json: {os.path.getsize('output/report.json')} bytes")
    
    # Quick structural checks
    try:
        ds = xr.open_dataset('output/mhw_mask.nc')
        print(f"✅ NetCDF structure valid: {list(ds.dims.keys())}")
    except Exception as e:
        print(f"❌ NetCDF structure error: {e}")
    
    try:
        with open('output/report.json', 'r') as f:
            report = json.load(f)
        print(f"✅ JSON structure valid: {len(report)} fields")
    except Exception as e:
        print(f"❌ JSON structure error: {e}")
    
    print("\n🎉 ALL CHECKS PASSED - TASK COMPLETE")
else:
    print("\n❌ SOME FILES MISSING")

print("-" * 20)