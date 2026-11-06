import fsspec, time
import numpy as np
import xarray as xr
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
t = ds.time.values.astype('datetime64[ns]').astype(object)
# check daily continuity
deltas = np.diff(ds.time.values.astype('timedelta64[ns]').astype('int64'))
print("n times:", len(t), "first:", t[0], "last:", t[-1])
print("all deltas 1 day:", np.all(deltas == np.timedelta64(1,'D')))
v = ds.analysed_sst
print("attrs:", v.attrs)
print("lat range:", ds.latitude.values[0], ds.latitude.values[-1], "lon:", ds.longitude.values[0], ds.longitude.values[-1])
