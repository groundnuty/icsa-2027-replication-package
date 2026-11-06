import xarray as xr, numpy as np, json
ds = xr.open_dataset('output/mhw_mask.nc', engine='netcdf4')
print(ds)
m = ds['mhw'].values
res = np.load('data/results.npz')
print('dtype:', m.dtype, 'shape:', m.shape)
print('matches computed mask:', np.array_equal(m, res['mhw']))
print('time first/last:', ds['time'].values[0], ds['time'].values[-1], 'n:', ds.sizes['time'])
print('lat range:', float(ds['lat'].values.min()), float(ds['lat'].values.max()))
print('lon range:', float(ds['lon'].values.min()), float(ds['lon'].values.max()))
print('sum mhw=1:', int(m.sum()))
# per-day totals
print('per-day totals:', m.sum(axis=(1,2)).tolist())
r = json.load(open('output/report.json'))
assert set(r.keys()) == {"region","baseline_analysed","target_analysed","events","complete","caveats"}
assert set(r['region'].keys()) == {"lat_min","lat_max","lon_min","lon_max"}
assert set(r['events'][0].keys()) == {"onset","end"}
print('report json OK')
print('event days consistency: mask first 1 on', str(ds['time'].values[m.sum(axis=(1,2)).argmax()])[:10], '(peak day)')
first_active = int(m.sum(axis=(1,2)).nonzero()[0][0]); last_active = int(len(m.sum(axis=(1,2)))-1 - m.sum(axis=(1,2))[::-1].nonzero()[0][0])
print('first/last active day:', str(ds['time'].values[first_active])[:10], str(ds['time'].values[last_active])[:10])
ds.close()