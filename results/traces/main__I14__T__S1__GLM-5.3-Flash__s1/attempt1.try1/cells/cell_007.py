import fsspec, xarray as xr, numpy as np, pandas as pd, time as timer, traceback
fs = fsspec.filesystem('onedata')
t0 = timer.time()
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
print("open took", round(timer.time()-t0,2), "s")
times = pd.DatetimeIndex(ds.time.values)
print("times daily & complete 1982-2023?", (times[0]==pd.Timestamp('1982-01-01'), times[-1]==pd.Timestamp('2023-12-31'), len(times)))
diffs = np.unique(np.diff(times.values).astype('timedelta64[D]').astype(int))
print("unique day diffs:", diffs)
# check needed ranges present
need = pd.date_range('1991-12-27','2003-01-05').append(pd.date_range('2015-06-01','2015-08-31'))
missing = need.difference(times)
print("missing needed dates:", len(missing))

lat = ds.latitude.values; lon = ds.longitude.values
latidx = np.where((lat >= 56.13 - 1e-6) & (lat <= 57.33 + 1e-6))[0]
lonidx = np.where((lon >= 17.71 - 1e-6) & (lon <= 18.91 + 1e-6))[0]
print(len(latidx), len(lonidx), lat[latidx[0]], lat[latidx[-1]], lon[lonidx[0]], lon[lonidx[-1]])

t0 = timer.time()
v = ds.analysed_sst.isel(time=1000, latitude=latidx, longitude=lonidx).values
print("one region day read:", round(timer.time()-t0,2), "s", v.shape, v.dtype)
t0 = timer.time()
v2 = ds.analysed_sst.isel(time=1001, latitude=latidx, longitude=lonidx).values
print("second region day read:", round(timer.time()-t0,2), "s")
t0 = timer.time()
v3 = ds.analysed_sst.isel(time=[1002,1003,1004], latitude=latidx, longitude=lonidx).values
print("3-day fancy read:", round(timer.time()-t0,2), "s", v3.shape)
