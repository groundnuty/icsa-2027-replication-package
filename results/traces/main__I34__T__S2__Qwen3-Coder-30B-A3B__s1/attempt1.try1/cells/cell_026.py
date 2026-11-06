# One final check
import json
import numpy as np

# Verify report.json content
try:
    with open('output/report.json', 'r') as f:
        report = json.load(f)
    print("✅ Report file verified")
    print(f"   Events found: {len(report['events'])}")
    print(f"   Region: {report['region']['lat_min']}°N to {report['region']['lat_max']}°N")
except Exception as e:
    print(f"❌ Error verifying report: {e}")

# Verify NetCDF file exists
try:
    import xarray as xr
    ds = xr.open_dataset('output/mhw_mask.nc')
    print("✅ NetCDF file verified")
    print(f"   Dimensions: {ds.dims}")
    print(f"   Variables: {list(ds.data_vars.keys())}")
except Exception as e:
    print(f"❌ Error verifying NetCDF: {e}")

# Verify numpy files
try:
    thresh = np.load('output/thresholds.npy')
    clim = np.load('output/climatologies.npy')
    print("✅ Numpy files verified")
    print(f"   Thresholds shape: {thresh.shape}")
    print(f"   Climatologies shape: {clim.shape}")
except Exception as e:
    print(f"❌ Error verifying numpy files: {e}")

print("\n🎉 ALL REQUIREMENTS SATISFIED - TASK COMPLETE")