import fsspec, xarray as xr, numpy as np, time, pandas as pd
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine="h5netcdf")

lat = ds.latitude.values.astype('float64')
lon = ds.longitude.values.astype('float64')
latm = (lat >= 59.05) & (lat <= 60.25)
lonm = (lon >= 21.25) & (lon <= 22.45)
li, lj = np.nonzero(latm), np.nonzero(lonm)
print('n lat', li[0].size, 'first/last idx', li[0][0], li[0][-1], 'lat', lat[li[0][0]], lat[li[0][-1]])
print('n lon', lj[0].size, 'first/last idx', lj[0][0], lj[0][-1], 'lon', lon[lj[0][0]], lon[lj[0][-1]])

td = pd.to_datetime(ds.time.values)
i0 = np.searchsorted(td.values, np.datetime64('1991-12-27'))
i1 = np.searchsorted(td.values, np.datetime64('2003-01-05'))
i2 = np.searchsorted(td.values, np.datetime64('2014-06-01'))
i3 = np.searchsorted(td.values, np.datetime64('2014-08-31'))
print('idx baseline', i0, i1, 'count', i1-i0+1, td[i0].astype(str), td[i1].astype(str))
print('idx target', i2, i3, 'count', i3-i2+1, td[i2].astype(str), td[i3].astype(str))
def contig(a,b):
    d = np.diff(ds.time.values[a:b+1].astype('int64'))
    return bool((d==86400000000000).all())
print('baseline contiguous', contig(i0,i1), 'target contiguous', contig(i2,i3))

t2=time.time()
sub = ds.analysed_sst.isel(time=range(i0, i0+20), latitude=li[0], longitude=lj[0]).values.astype('float64')
t3=time.time()
print('read 20 days region: shape', sub.shape, 'elapsed %.1fs' % (t3-t2))
fin = sub[np.isfinite(sub)]
print('sample values:', fin[:10])
print('nan fraction:', np.mean(~np.isfinite(sub)))
