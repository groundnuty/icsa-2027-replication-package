import numpy as np, json, xarray as xr
ds = xr.open_dataset('output/mhw_mask.nc')
print(ds)
m = ds['mhw']
assert m.dtype == np.uint8, m.dtype
assert m.dims == ('time','lat','lon'), m.dims
assert m.shape == (92, 60, 60)
print('time:', ds.time.values[0], '->', ds.time.values[-1])
print('lat range:', ds.lat.values[0], ds.lat.values[-1], '| lon range:', ds.lon.values[0], ds.lon.values[-1])
st = np.load('/tmp/mhw_state.npz')
cellmhw = st['cellmhw'].reshape(92,60,60)
mm = m.values
assert (mm == cellmhw.astype(np.uint8)).all(), 'mask mismatch vs computed cellmhw'
print('mask matches computed per-cell MHW array: True')
print('total mhw=1 cells-days:', int(mm.sum()), '| per-day counts first/last event:')
for d in range(92):
    c = int(mm[d].sum())
    if c and (d==0 or mm[d-1].sum()==0 or mm[d+1].sum()==0 if d<91 else c and True):
        pass
act = mm.max(axis=(1,2))
from datetime import date, timedelta
tt = [date(2014,6,1)+timedelta(days=k) for k in range(92)]
prev = False
for d in range(92):
    if act[d] != prev:
        print(('event start ' if act[d] else 'event end '), tt[d].isoformat())
    prev = act[d]
rep = json.load(open('output/report.json'))
assert set(rep.keys()) == {"region","baseline_analysed","target_analysed","events","complete","caveats"}
assert set(rep['region'].keys()) == {"lat_min","lat_max","lon_min","lon_max"}
for e in rep['events']: assert set(e.keys()) == {"onset","end"}
print('report OK:', json.dumps(rep['events']))
print('ALL VALIDATIONS PASSED')
