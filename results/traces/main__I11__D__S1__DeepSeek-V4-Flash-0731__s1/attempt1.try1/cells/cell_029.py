
import json
import xarray as xr
import numpy as np

# Verify report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)

print("Report:")
print(json.dumps(report, indent=2))

# Verify all required fields
required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required_fields:
    if field not in report:
        print(f"MISSING FIELD: {field}")
    else:
        print(f"  {field}: present")

# Check region values
print(f"\nRegion: {report['region']}")
print(f"Lat range: {report['region']['lat_min']} to {report['region']['lat_max']}")
print(f"Lon range: {report['region']['lon_min']} to {report['region']['lon_max']}")

# Check baseline
print(f"Baseline: {report['baseline_analysed']}")
print(f"Target: {report['target_analysed']}")
print(f"Events: {report['events']}")
print(f"Complete: {report['complete']}")
print(f"Caveats: '{report['caveats']}'")

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(f"\nmhw_mask.nc:")
print(f"  Variables: {list(ds.data_vars)}")
print(f"  Dimensions: {dict(ds.sizes)}")
print(f"  mhw dtype: {ds['mhw'].dtype}")
print(f"  time: {ds.time.values[0]} to {ds.time.values[-1]}, n={len(ds.time)}")
print(f"  lat: {ds.lat.values[0]} to {ds.lat.values[-1]}, n={len(ds.lat)}")
print(f"  lon: {ds.lon.values[0]} to {ds.lon.values[-1]}, n={len(ds.lon)}")
print(f"  mhw values: {np.unique(ds['mhw'].values)}")

# Check that mhw is uint8
print(f"  mhw dtype: {ds['mhw'].dtype}")
