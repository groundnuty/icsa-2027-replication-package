import numpy as np, xarray as xr, json, datetime as dt
chk = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
m = chk.mhw.values
tdates = [dt.date(2010,6,1)+dt.timedelta(days=i) for i in range(m.shape[0])]
act = m.any(axis=(1,2))
# event boundaries
e0 = tdates.index(dt.date(2010,6,27)); e1 = tdates.index(dt.date(2010,7,26))
print('active 06-26:', act[e0-1], '| active 06-27:', act[e0], '| active 07-26:', act[e1], '| active 07-27:', act[e1+1])
print('mask zero outside event:', m[:e0].sum()==0 and m[e1+1:].sum()==0)
print('cells in MHW per active day: min/max:', m[e0:e1+1].sum(axis=(1,2)).min(), m[e0:e1+1].sum(axis=(1,2)).max())
print('land cells all zero:', (m[:, ~np.isfinite(np.load("/work/targ_sst.npy")).all(axis=0)]==0).all())
# exact fields check
r = json.load(open('output/report.json'))
print('report keys:', sorted(r.keys()))
print(json.dumps(r))
