import xarray as xr, numpy as np, json
out = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(out)
mhw = out['mhw']
print('dtype:', mhw.dtype, '| unique values:', np.unique(mhw.values))
print('mask sum:', int(mhw.values.sum()))
# cross-check against pipeline result
mask_ref = np.load('/work/mask.npy')
print('matches pipeline mask exactly:', np.array_equal(mhw.values.astype(bool), mask_ref))
print('time:', str(out.time.values[0])[:10], '->', str(out.time.values[-1])[:10], '| n =', out.sizes['time'])
print('lat:', out.lat.values[0], '->', out.lat.values[-1], '| lon:', out.lon.values[0], '->', out.lon.values[-1])
# land rows all zero?
landc = np.isnan(np.load('/work/tgt.npy')[0])
print('land cells all zero in mhw:', (mhw.values[:, landc] == 0).all())
rep = json.load(open('output/report.json'))
print('\nreport keys:', sorted(rep.keys()))
print(json.dumps(rep, indent=1))