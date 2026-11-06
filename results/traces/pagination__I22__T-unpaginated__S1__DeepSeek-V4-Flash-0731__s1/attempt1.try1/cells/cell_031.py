
import os
import json
import xarray as xr
import numpy as np

# Check files exist
print('Files in output:')
for f in os.listdir('output'):
    print(f'  {f}')

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(f'\nmhw_mask.nc:')
print(f'  Shape: {ds["mhw"].shape}')
print(f'  Dtype: {ds["mhw"].dtype}')
print(f'  Time range: {ds["time"].values[0]} to {ds["time"].values[-1]}')
print(f'  Lat range: {ds["lat"].values[0]:.4f} to {ds["lat"].values[-1]:.4f}')
print(f'  Lon range: {ds["lon"].values[0]:.4f} to {ds["lon"].values[-1]:.4f}')
print(f'  Sum: {ds["mhw"].values.sum()}')
print(f'  Unique values: {np.unique(ds["mhw"].values)}')
ds.close()

# Verify report.json
with open('output/report.json') as f:
    report = json.load(f)
print(f'\nreport.json:')
print(json.dumps(report, indent=2))

# Check required fields
required = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required:
    if field not in report:
        print(f'  MISSING: {field}')
    else:
        print(f'  OK: {field}')

# Verify region
region = report['region']
assert region['lat_min'] == 57.41
assert region['lat_max'] == 58.61
assert region['lon_min'] == 18.69
assert region['lon_max'] == 19.89
print('Region OK')

# Verify events format
events = report['events']
assert isinstance(events, list)
for ev in events:
    assert set(ev.keys()) == {'onset', 'end'}
    assert isinstance(ev['onset'], str)
    assert isinstance(ev['end'], str)
print('Events format OK')

print('\nAll checks passed!')
