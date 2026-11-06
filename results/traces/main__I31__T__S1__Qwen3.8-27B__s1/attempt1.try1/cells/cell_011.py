
import fsspec, xarray as xr, numpy as np, time, pickle, os
fs = fsspec.filesystem('onedata')
f = fs.open('/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
tvals = ds.time.values  # datetime64[ns]
def tidx(dt):
    i = int(np.searchsorted(tvals, np.datetime64(dt)))
    assert tvals[i] == np.datetime64(dt), (dt, tvals[i])
    return i
print("1991-12-27:", tidx('1991-12-27'), "2003-01-05:", tidx('2003-01-05'))
print("2017-06-01:", tidx('2017-06-01'), "2017-08-31:", tidx('2017-08-31'))
# check every expected date is present in the dataset time
import datetime
miss = []
d = datetime.date(1991,12,27)
while d <= datetime.date(2003,1,5):
    if not (tvals == np.datetime64(d)).any(): miss.append(str(d))
    d += datetime.timedelta(days=1)
d = datetime.date(2017,6,1)
while d <= datetime.date(2017,8,31):
    if not (tvals == np.datetime64(d)).any(): miss.append(str(d))
    d += datetime.timedelta(days=1)
print("missing dates:", miss)
ds.close()
