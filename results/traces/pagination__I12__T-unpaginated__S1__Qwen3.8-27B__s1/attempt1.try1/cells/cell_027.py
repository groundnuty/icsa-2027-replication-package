import xarray as xr, json
import numpy as np
ds = xr.open_dataset('output/mhw_mask.nc')
print(ds)
v = ds.mhw
print('dtype', v.dtype, 'dims', v.dims, 'shape', v.shape)
print('time', v.time.values[0], '->', v.time.values[-1], 'n=', len(v.time))
print('lat', float(v.lat.values[0]), '->', float(v.lat.values[-1]), 'n=', len(v.lat))
print('lon', float(v.lon.values[0]), '->', float(v.lon.values[-1]), 'n=', len(v.lon))
m = v.values
print('unique values:', np.unique(m))
print('total MHW cell-days:', int(m.sum()))
days_with = np.where(m.sum(axis=(1,2)) > 0)[0]
print('active days:', len(days_with), v.time.values[days_with[0]], '->', v.time.values[days_with[-1]])
# recompute active from saved mask for cross-check
mask = np.load('/tmp/mhw_mask.npy')
assert np.array_equal(m, mask.reshape(92,60,60).astype(np.uint8))
print('mask matches computed result: True')
print(json.dumps(json.load(open('output/report.json')), indent=2))
ds.close()