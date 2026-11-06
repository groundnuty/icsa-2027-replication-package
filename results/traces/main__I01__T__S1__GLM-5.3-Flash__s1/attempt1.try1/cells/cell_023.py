import numpy as np, json
import xarray as xr

ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(ds)
m = ds.mhw.values
print('dtype:', ds.mhw.dtype, '| dims:', ds.mhw.dims, '| shape:', m.shape)
print('time[0], time[-1]:', str(ds.time.values[0])[:10], str(ds.time.values[-1])[:10], '| n =', ds.time.size)
print('lat:', float(ds.lat[0]), '..', float(ds.lat[-1]), '| lon:', float(ds.lon[0]), '..', float(ds.lon[-1]))
print('unique values:', np.unique(m))

z1 = np.load('/work/cache_stage1.npz')
z3 = np.load('/work/cache_stage3.npz')
sea = z1['sea']                       # (60,60)
mask = z3['mhw_span'].reshape(92, 60, 60)
print('identical to computed mask:', bool(np.array_equal(m.astype(bool), mask)))
print('land cells all zero:', bool((m[:, ~sea] == 0).all()))
print('MHW cell-days:', int(m.sum()))
active = m.any(axis=(1,2))
runs = []
inrun = False
for i, a in enumerate(active):
    if a and not inrun: s = i; inrun = True
    if not a and inrun: runs.append((s, i-1)); inrun = False
if inrun: runs.append((s, len(active)-1))
d0 = np.datetime64('2008-06-01')
print('active-day runs from file:', [(str(d0+np.int64(s)), str(d0+np.int64(e))) for s, e in runs])

rep = json.load(open('output/report.json'))
assert set(rep.keys()) == {"region","baseline_analysed","target_analysed","events","complete","caveats"}
assert set(rep["region"]) == {"lat_min","lat_max","lon_min","lon_max"}
assert all(set(e) == {"onset","end"} for e in rep["events"])
print('report.json keys OK:', json.dumps(rep["events"]))
import os
print('files:', os.path.getsize('output/mhw_mask.nc'), 'bytes nc;', os.path.getsize('output/report.json'), 'bytes json')
