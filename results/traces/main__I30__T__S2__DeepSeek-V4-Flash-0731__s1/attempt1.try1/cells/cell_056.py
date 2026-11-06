
import xarray as xr
import json
import numpy as np

# Verify NetCDF output
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("=== NetCDF Verification ===")
print("Dimensions:", dict(ds.sizes))
print("Variables:", list(ds.data_vars))
print("mhw dtype:", ds['mhw'].dtype)
print("mhw shape:", ds['mhw'].shape)
print("mhw unique values:", np.unique(ds['mhw'].values))
print("mhw sum:", int(ds['mhw'].sum().values))
print("time range:", str(ds['time'].values[0])[:10], "to", str(ds['time'].values[-1])[:10])
print("lat range:", float(ds['latitude'].values[0]), "to", float(ds['latitude'].values[-1]))
print("lon range:", float(ds['longitude'].values[0]), "to", float(ds['longitude'].values[-1]))

# Verify report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)
print("\n=== Report Verification ===")
print("Fields:", list(report.keys()))
print("region:", report['region'])
print("baseline_analysed:", report['baseline_analysed'])
print("target_analysed:", report['target_analysed'])
print("events:", report['events'])
print("complete:", report['complete'])
print("caveats:", repr(report['caveats']))

# Check required fields
required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required_fields:
    assert field in report, f"Missing field: {field}"
print("\nAll required fields present.")

# Verify region
assert report['region'] == {"lat_min": 58.69, "lat_max": 59.89, "lon_min": 18.69, "lon_max": 19.89}
print("Region correct.")

# Verify events format
for ev in report['events']:
    assert 'onset' in ev and 'end' in ev, f"Event missing onset/end: {ev}"
    assert len(ev['onset']) == 10 and len(ev['end']) == 10, f"Invalid date format: {ev}"
print("Events format correct.")

# Verify the mhw values match the computed mask
mhw_mask = np.load('/tmp/mhw_mask.npy')
assert np.array_equal(ds['mhw'].values, mhw_mask.astype(np.uint8)), "mhw values don't match"
print("mhw values match computed mask.")

# Check land cells are 0
sea_mask = np.load('/tmp/sea_mask.npy')
land = ~sea_mask
assert ds['mhw'].values[:, land].max() == 0, "Land cells should be 0"
print("Land cells are 0.")

ds.close()
print("\nAll verifications passed!")
