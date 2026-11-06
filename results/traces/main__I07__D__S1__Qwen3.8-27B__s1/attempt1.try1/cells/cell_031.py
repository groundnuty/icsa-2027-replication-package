import numpy as np, xarray as xr
ds = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
print(ds)
m = ds['mhw'].values
print("dtype:", m.dtype, "shape:", m.shape)
print("time[0]:", ds.time.values[0], "time[-1]:", ds.time.values[-1])
print("lat range:", float(ds.lat.values[0]), float(ds.lat.values[-1]), "n:", ds.lat.size)
print("lon range:", float(ds.lon.values[0]), float(ds.lon.values[-1]), "n:", ds.lon.size)
print("total mhw=1:", int(m.sum()))
# land cells must be 0
S_tgt = np.load('/work/S_tgt.npy')
sea = np.isfinite(S_tgt).all(axis=0)
print("land all zero:", (m[:, ~sea] == 0).all())
# event days
active = m.reshape(92, -1).sum(axis=1) > 0
print("first active:", ds.time.values[np.argmax(active)], "last active:", ds.time.values[91-np.argmax(active[::-1])])
ds.close()

# Independent single-cell end-to-end check (fresh code path, from raw files)
import fsspec
from datetime import date, timedelta
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
lat_vals = np.load('/work/lat_vals.npy'); lon_vals = np.load('/work/lon_vals.npy')
ci, cj = 30, 30  # a cell near region centre
def read_region(dt):
    p = f"/work/data/sst_{dt.year:04d}{dt.month:02d}{dt.day:02d}.nc"
    d2 = xr.open_dataset(p, engine='h5netcdf')
    a = d2['analysed_sst'].values[0]; la = d2.latitude.values; lo = d2.longitude.values
    d2.close()
    ii = int(np.where(la == lat_vals[ci])[0]); jj = int(np.where(lo == lon_vals[cj])[0])
    return float(a[ii, jj])

def doy_of(dt): return (date(2000, dt.month, dt.day) - date(2000,1,1)).days + 1

# pool for doy 153 (June 1), this cell: 11 windows around June 1 of 1992..2002
pool = []
for y in range(1992, 2003):
    b = date(y, 6, 1)
    for k in range(-5, 6):
        pool.append(read_region(b + timedelta(days=k)))
pool = np.array(pool)
print("pool n:", len(pool), "finite:", np.isfinite(pool).sum())
q_hazen = np.quantile(pool, 0.9, method='hazen')
# smoothing: need smoothed threshold for doy 153 = mean of thr[138..168] (doy 153-15..153+15)
# compute raw thr for those 31 doys
raw_thr = np.empty(31)
for j, dd in enumerate(range(153-15, 153+16)):
    md = (date(2000,1,1) + timedelta(days=dd-1))  # (month,day) for this doy
    pool2 = []
    for y in range(1992, 2003):
        b = date(y, md.month, md.day)
        for k in range(-5, 6):
            pool2.append(read_region(b + timedelta(days=k)))
    raw_thr[j] = np.quantile(pool2, 0.9, method='hazen')
thr_smooth_153 = raw_thr.mean()
print("independent smoothed thr for this cell doy153:", thr_smooth_153)
# compare with saved thr_s
thr_s = np.load('/work/thr_s.npy')
saved = thr_s[153-1, ci*60+cj]
print("saved thr_s:", saved, "match:", np.isclose(thr_smooth_153, saved))
# now check hot days around onset
for dt in [date(2021,6,1), date(2021,6,2), date(2021,6,5), date(2021,6,6)]:
    sst = read_region(dt)
    t = thr_s[doy_of(dt)-1, ci*60+cj]
    print(dt, "sst:", sst, "thr:", t, "hot:", sst >= t)
