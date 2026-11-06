import numpy as np, xarray as xr, json, os
# verify written files
p = 'output/mhw_mask.nc'
ds = xr.open_dataset(p, engine='h5netcdf')
print(ds)
m = ds['mhw']
print('dtype:', m.dtype, 'shape:', m.shape, 'sum:', int(m.values.sum()))
print('time[0], time[-1]:', ds.time.values[0], ds.time.values[-1], 'n =', ds.sizes['time'])
print('lat range:', float(ds.lat.min()), float(ds.lat.max()))
print('lon range:', float(ds.lon.min()), float(ds.lon.max()))
# check values are only 0/1
print('unique values:', np.unique(m.values))
# check land cells all zero
data = np.load('/tmp/sst_needed.npy')
target = data[4028:]
sea = np.isfinite(target).all(axis=0)
mhw = m.values
print('any mhw=1 on land?', bool(mhw[:, ~sea].any()))
print('mhw sum on sea cells:', int(mhw[:, sea].sum()))
# report
with open('output/report.json') as f:
    rep = json.load(f)
print('report keys:', sorted(rep.keys()))
print('events:', rep['events'])
print('complete:', rep['complete'])
print('file sizes:', {f: os.path.getsize(os.path.join('output',f)) for f in os.listdir('output')})
