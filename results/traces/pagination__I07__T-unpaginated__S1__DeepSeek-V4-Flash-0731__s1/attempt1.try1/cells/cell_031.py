
import xarray as xr
import numpy as np

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds.mhw.values
sea_cells = np.load('/tmp/sea_cells.npy')

# Verify land cells are 0
land_mask = ~sea_cells
land_values = mhw[:, land_mask]
print(f"Land cell mhw values (should all be 0): min={land_values.min()}, max={land_values.max()}")

# Verify sea cells have correct values
sea_values = mhw[:, sea_cells]
print(f"Sea cell mhw values: min={sea_values.min()}, max={sea_values.max()}")

# Verify dimensions
print(f"Dimensions: time={ds.dims['time']}, lat={ds.dims['lat']}, lon={ds.dims['lon']}")
print(f"mhw dtype: {ds.mhw.dtype}")

# Check report.json
import json
with open('output/report.json') as f:
    report = json.load(f)

# Verify all required fields
required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required_fields:
    assert field in report, f"Missing field: {field}"
print(f"\nAll required fields present in report.json")

# Verify region
assert report['region'] == {"lat_min": 54.45, "lat_max": 55.65, "lon_min": 16.05, "lon_max": 17.25}
print(f"Region correct: {report['region']}")

# Verify baseline_analysed
assert report['baseline_analysed'] == {"start": "1991-12-27", "end": "2003-01-05"}
print(f"Baseline analysed correct: {report['baseline_analysed']}")

# Verify target_analysed
assert report['target_analysed'] == {"start": "2021-06-01", "end": "2021-08-31"}
print(f"Target analysed correct: {report['target_analysed']}")

# Verify events
print(f"Events: {report['events']}")
assert len(report['events']) == 1
assert report['events'][0] == {"onset": "2021-06-01", "end": "2021-08-08"}
print(f"Events correct")

# Verify complete and caveats
assert report['complete'] == True
assert isinstance(report['caveats'], str)
print(f"Complete: {report['complete']}")
print(f"Caveats: '{report['caveats']}'")

print("\nAll verifications passed!")
