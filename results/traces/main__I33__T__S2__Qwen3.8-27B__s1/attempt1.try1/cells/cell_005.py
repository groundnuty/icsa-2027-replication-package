import fsspec, xarray as xr, numpy as np, time
fs = fsspec.filesystem('onedata')
t0=time.time()
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine="h5netcdf")
t1=time.time()
print('open time', t1-t0)

lat = ds.latitude.values.astype(float64) if hasattr(np,'float64') else ds.latitude.values.astype('float64')
lon = ds.longitude.values.astype('float64')
latm = (lat >= 59.05) & (lat <= 60.25)
lonm = (lon >= 21.25) & (lon <= 22.45)
li, lj = np.nonzero(latm), np.nonzero(lonm)
print('n lat', li[0].size, li[0][0], li[0][-1], 'lat range', lat[li[0][0]], lat[li[0][-1]])
print('n lon', lj[0].size, lj[0][0], lj[0][-1], 'lon range', lon[lj[0][0]], lon[lj[0][-1]])

# time indices
times = ds.time.values
import pandas as pd
td = pd.to_datetime(times)
i0 = np.searchsorted(td.values, np.datetime64('1991-12-27'))
i1 = np.searchsorted(td.values, np.datetime64('2003-01-05'))
i2 = np.searchsorted(td.values, np.datetime64('2014-06-01'))
i3 = np.searchsorted(td.values, np.datetime64('2014-08-31'))
print('idx baseline', i0, i1, 'count', i1-i0+1, td[i0].astype(str), td[i1].astype(str))
print('idx target', i2, i3, 'count', i3-i2+1, td[i2].astype(str), td[i3].astype(str))
# check contiguity
def contig(i0,i1):
    d = np.diff(td[i0:i1+1].astype('int64'))
    return int((d==86400000000000).all())
print('baseline contiguous', contig(i0,i1), 'target contiguous', contig(i2,i3))

# test read speed: 20 days of region
t2=time.time()
sub = ds.analysed_sst.isel(time=range(i0, i0+20), latitude=li[0], longitude=lj[0]).values.astype('float64')
t3=time.time()
print('read 20 days region: shape', sub.shape, 'elapsed %.1fs' % (t3-t2))
print('sample values:', sub[np.isfinite(sub)][:10])
print('nan fraction:', np.mean(~np.isfinite(sub)))
