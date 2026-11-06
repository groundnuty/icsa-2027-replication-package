import fsspec, time, numpy as np, h5py, datetime as dt

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f = fs.open(path, 'rb')
hf = h5py.File(f, 'r')
d = hf['analysed_sst']

tv = hf['time'][:]
base = np.datetime64('1981-01-01')
times = base + tv.astype('timedelta64[s]')
print("time[0]", times[0], "time[-1]", times[-1], "n", len(times))
dd = np.diff(times).astype('timedelta64[D]').astype(int)
print("unique day steps:", np.unique(dd))
# index of a date
def idx_of(datestr):
    return int((np.datetime64(datestr) - np.datetime64('1982-01-01')) / np.timedelta64(1, 'D'))
print("idx 1991-12-27:", idx_of('1991-12-27'), "date check:", times[idx_of('1991-12-27')])
print("idx 2003-01-05:", idx_of('2003-01-05'), "date check:", times[idx_of('2003-01-05')])
print("idx 2019-06-01:", idx_of('2019-06-01'), "date check:", times[idx_of('2019-06-01')])
print("idx 2019-08-31:", idx_of('2019-08-31'), "date check:", times[idx_of('2019-08-31')])

i0,i1,j0,j1 = 545,605,721,781

# timing test: 30 consecutive days in 1995
t0 = time.time()
a = d[idx_of('1995-07-01'):idx_of('1995-07-01')+30, i0:i1, j0:j1]
t1 = time.time()
print("read 30 days 1995:", round(t1-t0,2), "s", a.shape, a.dtype)
print("nan frac 1995-07:", np.isnan(a).mean(), "min/max K:", np.nanmin(a), np.nanmax(a))
# count of cells finite on a summer day
fin = np.isfinite(a[0])
print("finite cells day0 1995-07-01:", fin.sum(), "/3600")

t0 = time.time()
b = d[idx_of('2019-07-01'):idx_of('2019-07-01')+30, i0:i1, j0:j1]
t1 = time.time()
print("read 30 days 2019:", round(t1-t0,2), "s")
print("nan frac 2019-07:", np.isnan(b).mean(), "min/max K:", np.nanmin(b), np.nanmax(b))
fin19 = np.isfinite(b[0])
print("finite cells 2019-07-01:", fin19.sum(), "/3600")
# per-day all-nan check on these samples
print("any day all-NaN (1995 sample):", [bool(np.all(~np.isfinite(a[k]))) for k in range(30)].count(True))
print("any day all-NaN (2019 sample):", [bool(np.all(~np.isfinite(b[k]))) for k in range(30)].count(True))
hf.close(); f.close()
