import xarray as xr, numpy as np, json, h5py
p = '/work/output/mhw_mask.nc'
ds = xr.open_dataset(p, engine='h5netcdf')
print(ds)
print('\nmhw dtype:', ds['mhw'].dtype, '| dims:', ds['mhw'].dims, '| shape:', ds['mhw'].shape)
m = ds['mhw'].values
print('mhw sum (should be 0):', int(m.sum()), '| unique values:', np.unique(m))
print('time:', ds['time'].values[0], '->', ds['time'].values[-1], '| n =', ds.time.size)
print('lat:', ds['lat'].values.min(), '->', ds['lat'].values.max(), '| lon:', ds['lon'].values.min(), '->', ds['lon'].values.max())
# confirm raw netcdf variable dtype is uint8 on disk
with h5py.File(p, 'r') as f:
    print('\nraw HDF5 dataset dtype:', f['mhw'].dtype, '| chunks:', f['mhw'].chunks)
    # coordinate values match dataset file
    with h5py.File('/data/icsa2027_data_20261101T090944Z/s1z/sst_20040615.nc', 'r') as g:
        print('lat matches source:', np.array_equal(f['lat'][:], g['latitude'][196:256]))
        print('lon matches source:', np.array_equal(f['lon'][:], g['longitude'][485:545]))
    print('time matches target days:', str(ds.time.values[0])[:10] == '2004-06-01', str(ds.time.values[-1])[:10] == '2004-08-31', ds.time.size == 92)
ds.close()
r = json.load(open('/work/output/report.json'))
print('\nreport.json keys:', sorted(r.keys()))
print('region:', r['region'])
print('baseline_analysed:', r['baseline_analysed'])
print('target_analysed:', r['target_analysed'])
print('events:', r['events'])
print('complete:', r['complete'])
print('caveats length:', len(r['caveats']))
