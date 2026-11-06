import xarray as xr, numpy as np, json

ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(ds)
m = ds['mhw']
print('dtype:', m.dtype, '| dims:', m.dims, '| shape:', m.shape)
assert m.dtype == np.uint8
assert m.dims == ('time','lat','lon')
vals = np.unique(m.values)
print('unique values:', vals)
assert set(vals) <= {0,1}
print('time first/last:', str(ds.time.values[0])[:10], str(ds.time.values[-1])[:10], 'n =', ds.sizes['time'])
print('lat range:', float(ds.lat.min()), float(ds.lat.max()))
print('lon range:', float(ds.lon.min()), float(ds.lon.max()))
assert float(ds.lat.min())>=60.49 and float(ds.lat.max())<=61.69
assert float(ds.lon.min())>=17.25 and float(ds.lon.max())<=18.45
ds.close()

r = json.load(open('output/report.json'))
print('\nreport keys:', sorted(r.keys()))
assert set(r.keys()) == {'region','baseline_analysed','target_analysed','events','complete','caveats'}
assert set(r['region'].keys()) == {'lat_min','lat_max','lon_min','lon_max'}
print('region:', r['region'])
print('baseline_analysed:', r['baseline_analysed'])
print('target_analysed:', r['target_analysed'])
print('events:', r['events'])
print('complete:', r['complete'])
print('caveats:', r['caveats'][:120], '...')

# cross-check events against mask
mask = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')['mhw'].values
days = np.array([str(t)[:10] for t in xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf').time.values])
active = (mask.sum(axis=(1,2)) > 0)
idx = np.flatnonzero(active)
assert r['events'] == [{'onset': days[idx[0]], 'end': days[idx[-1]]}]
print('\nall checks passed: event in report matches mask in mhw_mask.nc')
