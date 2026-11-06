import fsspec, xarray as xr, numpy as np, time, pandas as pd
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine="h5netcdf")
lat = ds.latitude.values.astype('float64'); lon = ds.longitude.values.astype('float64')
li = np.nonzero((lat>=59.05)&(lat<=60.25))[0]; lj = np.nonzero((lon>=21.25)&(lon<=22.45))[0]
td = pd.to_datetime(ds.time.values)
i0 = int(np.searchsorted(td.values, np.datetime64('1991-12-27')))
i1 = int(np.searchsorted(td.values, np.datetime64('2003-01-05')))
i2 = int(np.searchsorted(td.values, np.datetime64('2014-06-01')))
i3 = int(np.searchsorted(td.values, np.datetime64('2014-08-31')))
print('baseline idx', i0, i1, 'count', i1-i0+1, str(td[i0].date()), str(td[i1].date()))
print('target idx', i2, i3, 'count', i3-i2+1, str(td[i2].date()), str(td[i3].date()))
d1 = np.diff(ds.time.values[i0:i1+1].astype('int64')); d2 = np.diff(ds.time.values[i2:i3+1].astype('int64'))
print('contig baseline', bool((d1==86400000000000).all()), 'contig target', bool((d2==86400000000000).all()))

t2=time.time()
sub = ds.analysed_sst.isel(time=range(i0, i0+20), latitude=li, longitude=lj).values.astype('float64')
t3=time.time()
print('read 20 days region: shape', sub.shape, 'elapsed %.1fs' % (t3-t2))
fin = sub[np.isfinite(sub)]
print('sample values (K):', fin[:10])
print('nan fraction:', np.mean(~np.isfinite(sub)))
