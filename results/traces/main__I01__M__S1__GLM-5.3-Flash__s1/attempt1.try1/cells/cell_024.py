import xarray as xr, numpy as np, json
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(ds)
print('mhw dtype:', ds.mhw.dtype, 'unique:', np.unique(ds.mhw.values))
print('time first/last:', ds.time.values[0], ds.time.values[-1], 'n:', ds.time.size)
print('lat range:', float(ds.lat.min()), float(ds.lat.max()))
print('lon range:', float(ds.lon.min()), float(ds.lon.max()))
print('sum:', int(ds.mhw.values.sum()))
# verify active days reproduce the single event
v = ds.mhw.values
act = v.any(axis=(1,2))
idx = np.where(act)[0]
print('active days:', idx.min(), idx.max(), 'count', act.sum())
rep = json.load(open('output/report.json'))
print('report keys:', list(rep.keys()))
assert set(rep.keys()) == {"region","baseline_analysed","target_analysed","events","complete","caveats"}
print('report OK')
ds.close()
