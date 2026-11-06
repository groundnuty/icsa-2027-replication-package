import numpy as np, xarray as xr, json, datetime as dt
# final verification
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
m = ds['mhw'].values
lat = ds['lat'].values; lon = ds['lon'].values; t = ds['time'].values
print('dims:', dict(ds.sizes), 'dtype:', ds['mhw'].dtype)
print('lat bounds:', lat.min(), lat.max(), '| lon bounds:', lon.min(), lon.max())
print('time:', str(t[0])[:10], '->', str(t[-1])[:10], len(t))
print('unique values:', np.unique(m), 'sum:', int(m.sum()))
# land cells (all-nan in SST target) must be 0
A=np.load('/tmp/A_all.npy'); sea=np.isfinite(A[4540:4632]).all(axis=0)
print('land cells all zero in mask?', bool((m[:,~sea]==0).all()), '| sea cells masked somewhere:', int((m[:,sea].sum(axis=0)>0).sum()))
ds.close()
rep=json.load(open('output/report.json'))
print('report keys:', sorted(rep.keys()))
print('events:', rep['events'])
