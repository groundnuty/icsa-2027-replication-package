import xarray as xr
import numpy as np
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
v = ds['analysed_sst']
print("attrs:", v.attrs)
print("encoding:", v.encoding)
print("units coord:", ds['time'].attrs, ds['latitude'].attrs, ds['longitude'].attrs)

lat = ds['latitude'].values
lon = ds['longitude'].values
t = ds['time'].values
print("lat range", lat.min(), lat.max(), "n=", len(lat))
print("lon range", lon.min(), lon.max(), "n=", len(lon))
print("time range", t.min(), t.max())

# region grid cells (inclusive bounds)
il = (lat >= 58.69) & (lat <= 59.89)
io = (lon >= 18.69) & (lon <= 19.89)
print("region cells:", il.sum(), io.sum())
print("lat vals:", lat[il][[0, -1]])
print("lon vals:", lon[io][[0, -1]])

# check daily contiguity in baseline and target windows
import datetime as dt
def idx(datestr):
    return int(np.searchsorted(t, np.datetime64(datestr)))
for s, e in [("1991-12-27","2003-01-05"), ("2017-06-01","2017-08-31")]:
    i0, i1 = idx(s), idx(e)
    seg = t[i0:i1+1]
    d = np.diff(seg.astype('int64')//10**9)
    print(s, e, "n_days=", len(seg), "all contiguous daily:", np.all(d==86400), "first/last:", seg[0], seg[-1])
ds.close()
