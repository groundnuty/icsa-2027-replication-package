# Final verification that files are properly formatted
import xarray as xr
import json

# Verify NetCDF structure
ds = xr.open_dataset('output/mhw_mask.nc')
assert ds.mhw.shape == (92, 60, 60), f"Unexpected shape: {ds.mhw.shape}"
assert ds.mhw.dtype == 'uint8', f"Unexpected dtype: {ds.mhw.dtype}"

# Verify JSON structure  
with open('output/report.json', 'r') as f:
    report = json.load(f)
    
assert report['region']['lat_min'] == 55.67
assert report['region']['lat_max'] == 56.87
assert report['region']['lon_min'] == 16.45
assert report['region']['lon_max'] == 17.65
assert report['baseline_analysed']['start'] == '1992-01-01'
assert report['baseline_analysed']['end'] == '2002-12-31'
assert report['target_analysed']['start'] == '2021-06-01'
assert report['target_analysed']['end'] == '2021-08-31'
assert report['complete'] == True
assert isinstance(report['events'], list)

print("All verifications passed successfully!")