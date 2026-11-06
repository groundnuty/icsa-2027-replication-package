
import json
import xarray as xr
import numpy as np

# Read back report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)

print('Report:')
print(json.dumps(report, indent=2))
print()

# Read back mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print('MHW mask:')
print('  Shape:', ds['mhw'].shape)
print('  Dtype:', ds['mhw'].dtype)
print('  Time:', ds['time'].values[0], 'to', ds['time'].values[-1])
print('  Lat:', ds['lat'].values[0], 'to', ds['lat'].values[-1])
print('  Lon:', ds['lon'].values[0], 'to', ds['lon'].values[-1])
print('  Unique values:', np.unique(ds['mhw'].values))
print('  Sum:', ds['mhw'].values.sum())
print()

# Verify the mask matches what we computed
print('Verification checks:')
print('  mhw[0] sum (June 1):', ds['mhw'].values[0].sum(), '- should be 0')
print('  mhw[1] sum (June 2):', ds['mhw'].values[1].sum(), '- should be 7')
print('  mhw[9] sum (June 10):', ds['mhw'].values[9].sum(), '- should be 846')
print('  mhw[10] sum (June 11):', ds['mhw'].values[10].sum(), '- should be 0')

# Check that land cells are 0
# Get lat/lon to verify region bounds
lat = ds['lat'].values
lon = ds['lon'].values
print('\nRegion bounds check:')
print(f'  lat: {lat.min()} to {lat.max()} (spec: 56.63 to 57.83)')
print(f'  lon: {lon.min()} to {lon.max()} (spec: 20.23 to 21.43)')
print(f'  All lat in [56.63, 57.83]: {np.all((lat >= 56.63) & (lat <= 57.83))}')
print(f'  All lon in [20.23, 21.43]: {np.all((lon >= 20.23) & (lon <= 21.43))}')

# Check report fields
print('\nReport field check:')
required = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required:
    print(f'  {field}: {"present" if field in report else "MISSING"}')
