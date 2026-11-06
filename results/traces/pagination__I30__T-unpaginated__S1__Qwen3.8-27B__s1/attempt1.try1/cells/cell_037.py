
import xarray, json, numpy as np, datetime as dt
ds = xarray.open_dataset('/work/output/mhw_mask.nc')
print(ds)
m = ds['mhw']
print('dtype:', m.dtype, 'dims:', m.dims, 'shape:', m.shape)
print('unique values:', np.unique(m.values))
print('time[0], time[-1]:', ds.time.values[0], ds.time.values[-1], 'n:', ds.sizes['time'])
print('lat range:', float(ds.lat.values.min()), float(ds.lat.values.max()), 'n:', ds.sizes['lat'])
print('lon range:', float(ds.lon.values.min()), float(ds.lon.values.max()), 'n:', ds.sizes['lon'])

mask = np.load('/work/mhw/mask.npy')
m3 = m.values
print('matches in-memory mask:', np.array_equal(m3, mask.reshape(92,60,60).astype(np.uint8)))
print('total 1s:', int(m3.sum()))
per_day = m3.sum(axis=(1,2))
print('event days (1-25 -> 29 Jun-25 Jul):', per_day[28:55].min(), per_day[28:55].max())
print('days outside event with 1s:', int(per_day[:28].sum() + per_day[55:].sum()))

r = json.load(open('/work/output/report.json'))
assert set(r.keys()) == {"region","baseline_analysed","target_analysed","events","complete","caveats"}
print('report OK:', r['events'], r['complete'])
print('lat/lon coord sample:', ds.lat.values[0], ds.lon.values[0], ds.lat.values[-1], ds.lon.values[-1])
