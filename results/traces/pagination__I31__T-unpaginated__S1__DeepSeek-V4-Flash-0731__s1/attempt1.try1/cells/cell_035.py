
import json
import numpy as np
import xarray as xr

# Check output files
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("mhw_mask.nc:")
print(f"  Shape: {ds.mhw.shape}")
print(f"  dtype: {ds.mhw.dtype}")
print(f"  Values: {np.unique(ds.mhw.values)}")
print(f"  Sum: {ds.mhw.values.sum()}")
print(f"  Time range: {ds.time.values[0]} to {ds.time.values[-1]}")
print(f"  Lat range: {ds.lat.values[0]} to {ds.lat.values[-1]}")
print(f"  Lon range: {ds.lon.values[0]} to {ds.lon.values[-1]}")
print(f"  Num time: {len(ds.time)}, Num lat: {len(ds.lat)}, Num lon: {len(ds.lon)}")

with open('output/report.json') as f:
    report = json.load(f)
print("\nreport.json:")
print(json.dumps(report, indent=2))
print()

# Verify all required fields are present
required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required_fields:
    assert field in report, f"Missing field: {field}"
    print(f"  Field '{field}': present")

# Verify region bounds
assert report['region']['lat_min'] == 58.69
assert report['region']['lat_max'] == 59.89
assert report['region']['lon_min'] == 18.69
assert report['region']['lon_max'] == 19.89
print("\nRegion bounds: correct")

# Verify baseline range
print(f"Baseline: {report['baseline_analysed']['start']} to {report['baseline_analysed']['end']}")
print(f"Target: {report['target_analysed']['start']} to {report['target_analysed']['end']}")

# Verify events
print(f"Events: {report['events']}")
print(f"Complete: {report['complete']}")
print(f"Caveats: {report['caveats']}")
