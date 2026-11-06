
import os
import json
import xarray as xr
import numpy as np

# Check files exist
print('Output directory contents:')
for f in os.listdir('output'):
    path = os.path.join('output', f)
    size = os.path.getsize(path)
    print(f'  {f}: {size} bytes')

# Verify report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)

print('\n=== Report Verification ===')
print('Keys:', list(report.keys()))
assert set(report.keys()) == {'region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats'}, 'Wrong keys in report'

print('Region:', report['region'])
assert report['region']['lat_min'] == 56.63
assert report['region']['lat_max'] == 57.83
assert report['region']['lon_min'] == 20.23
assert report['region']['lon_max'] == 21.43

print('Baseline analysed:', report['baseline_analysed'])
print('Target analysed:', report['target_analysed'])
print('Events:', report['events'])
print('Complete:', report['complete'])
print('Caveats:', repr(report['caveats']))

# Verify mhw_mask.nc
print('\n=== MHW Mask Verification ===')
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print('Dimensions:', dict(ds.sizes))
print('Variables:', list(ds.data_vars))
print('mhw dtype:', ds['mhw'].dtype)
print('mhw shape:', ds['mhw'].shape)
print('mhw values:', np.unique(ds['mhw'].values))
print('mhw sum:', ds['mhw'].values.sum())

# Verify time, lat, lon
print('\nCoordinates:')
print('  time:', ds['time'].values[0], 'to', ds['time'].values[-1], f'({len(ds["time"])} values)')
print('  lat:', ds['lat'].values[0], 'to', ds['lat'].values[-1], f'({len(ds["lat"])} values)')
print('  lon:', ds['lon'].values[0], 'to', ds['lon'].values[-1], f'({len(ds["lon"])} values)')

# Verify all bounds
assert len(ds['time']) == 92
assert len(ds['lat']) == 60
assert len(ds['lon']) == 60
assert np.all((ds['lat'].values >= 56.63) & (ds['lat'].values <= 57.83))
assert np.all((ds['lon'].values >= 20.23) & (ds['lon'].values <= 21.43))
assert ds['mhw'].dtype == np.uint8

# Verify mask values
mhw_vals = ds['mhw'].values
assert np.all((mhw_vals == 0) | (mhw_vals == 1)), 'Mask should only contain 0 and 1'
print('\nAll verification checks passed!')

# Final summary of results
print('\n=== Summary ===')
print(f'Region: lat {report["region"]["lat_min"]}-{report["region"]["lat_max"]}, lon {report["region"]["lon_min"]}-{report["region"]["lon_max"]}')
print(f'Target period: {report["target_analysed"]["start"]} to {report["target_analysed"]["end"]}')
print(f'Sea cells: 3304 out of 3600')
print(f'Regional events: {len(report["events"])}')
for ev in report['events']:
    print(f'  {ev["onset"]} to {ev["end"]}')
print(f'Total cell-days in MHW: {mhw_vals.sum()}')
