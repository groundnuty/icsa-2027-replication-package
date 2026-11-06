
import os, json, time, pickle
import numpy as np
import xarray as xr

t0 = time.time()
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")
t = ds.time.values
lat = ds.latitude.values; lon = ds.longitude.values

latm = (lat >= 56.63) & (lat <= 57.83)
lonm = (lon >= 20.23) & (lon <= 21.43)
i0, i1 = 3647, 7674    # 1991-12-27 .. 2003-01-05
j0, j1 = 10378, 10469  # 2010-06-01 .. 2010-08-31
t_bas = t[i0:i1+1]; t_tgt = t[j0:j1+1]
assert np.all(np.diff(t_bas) == np.timedelta64(1,'D')) and np.all(np.diff(t_tgt) == np.timedelta64(1,'D'))

bas = ds.analysed_sst.isel(time=slice(i0, i1+1)).values.astype("float64")
tgt = ds.analysed_sst.isel(time=slice(j0, j1+1)).values.astype("float64")
print("shapes:", bas.shape, tgt.shape, "load", round(time.time()-t0,1), "s")

sea2 = np.isfinite(tgt).all(axis=0)
si = np.argwhere(sea2)
n_sea = si.shape[0]
print("n sea cells:", n_sea, "of", sea2.size)
X_bas = np.ascontiguousarray(bas[:, si[:,0], si[:,1]].T)   # (4028, n_sea)
X_tgt = np.ascontiguousarray(tgt[:, si[:,0], si[:,1]].T)   # (92, n_sea)
print("baseline finite frac (sea cells):", np.isfinite(X_bas).mean())
print("sea cells with any baseline NaN:", int((np.isfinite(X_bas).sum(axis=0) < X_bas.shape[0]).sum()))

# --- day-of-year mapping (by month and day, Feb 29 = 60) ---
mlen = [31,29,31,30,31,30,31,31,30,31,30,31]
mdoy = np.zeros((12,31), int)
off = 0
for m in range(12):
    mdoy[m, :mlen[m]] = off + 1 + np.arange(mlen[m])
    off += mlen[m]
assert mdoy[1,27] == 59 and mdoy[1,28] == 60 and mdoy[2,0] == 61 and mdoy[11,30] == 366
doy2md = np.zeros((366,2), int)
for m in range(12):
    for day in range(1, mlen[m]+1):
        doy2md[mdoy[m, day-1]-1] = [m+1, day]
doy_t = np.array([mdoy[int(np.datetime64(dt,'M').astype(int)) % 100 - 1,
                       int(np.datetime64(dt,'D').astype(int) - np.datetime64(np.datetime64(dt,'M'),'D').astype(int))]
                  for dt in t_tgt])
print("target doys:", doy_t.min(), doy_t.max())

# --- per sea cell: pool for each day-of-year ---
years = np.arange(1992, 2003)
tb = t_bas
L = len(tb)
def bidx(y, m, d):
    di = int(np.searchsorted(tb, np.datetime64(y, m, d)))
    assert tb[di] == np.datetime64(y, m, d)
    return di
t1 = time.time()
thr = np.full((n_sea, 366), np.nan)
clim = np.full((n_sea, 366), np.nan)
bad_pool = 0
for d in range(1, 367):
    if d == 60:
        continue
    m, dd = doy2md[d-1]
    mask = np.zeros(L, bool)
    for y in years:
        bi = bidx(y, m, dd)
        s = max(0, bi-5); e = min(L-1, bi+5)
        mask[s:e+1] = True
    k = int(mask.sum())
    assert k == 121, (d, k)
    vals = X_bas[mask]
    nn = np.isfinite(vals).sum(axis=0)
    good = nn > 0
    if (~good).any():
        bad_pool += 1
    if good.any():
        vv = vals[:, good]
        thr[good, d-1] = np.nanpercentile(vv, 90, axis=0, method="hazen")
        clim[good, d-1] = np.nanmean(vv, axis=0)
print("pool loop", round(time.time()-t1,1), "s; all-NaN pools:", bad_pool)

# day 60 = mean of days 59 and 61
thr[:, 59] = 0.5 * (thr[:, 58] + thr[:, 60])
clim[:, 59] = 0.5 * (clim[:, 58] + clim[:, 60])
print("thr NaN count:", int(np.isnan(thr).sum()), "clim NaN count:", int(np.isnan(clim).sum()))

# --- 31-day centred moving mean with wrap ---
di = np.arange(366)
A = np.zeros((366, 366))
for i in range(366):
    A[(di - 15 + np.arange(31)) % 366, i] = 1.0
A /= 31.0
# check row sums and wrap behaviour
assert np.allclose(A.sum(axis=0), 1.0)
assert A[(0-15+np.arange(31))%366, 0].sum() == 31
thrS = thr @ A
climS = clim @ A
print("thrS NaN count:", int(np.isnan(thrS).sum()))

# --- hot days in target period ---
thr_t = thrS[:, doy_t - 1].T          # (92, n_sea)
hot = X_tgt >= thr_t                  # NaN threshold -> False
print("hot fraction:", hot.mean().round(5))

# --- per-cell MHWs (>=5 hot days, join gaps of 1-2) ---
mhw = np.zeros((len(t_tgt), n_sea), np.uint8)
ncells_with = 0
t2 = time.time()
for c in range(n_sea):
    h = hot[:, c]
    if not h.any():
        continue
    dd = np.diff(np.concatenate(([0], h, [0])))
    starts = np.flatnonzero(dd == 1)
    ends = np.flatnonzero(dd == -1) - 1
    sel = (ends - starts + 1) >= 5
    starts, ends = starts[sel], ends[sel]
    ms, me = [], []
    for s, e in zip(starts, ends):
        if me and (s - me[-1] - 1) <= 2:
            me[-1] = e
        else:
            ms.append(s); me.append(e)
    if ms:
        ncells_with += 1
        for s, e in zip(ms, me):
            mhw[s:e+1, c] = 1
print("mhw loop", round(time.time()-t2,1), "s; cells with >=1 MHW:", ncells_with)

# --- regional events ---
active = (mhw > 0).any(axis=1)
da = np.diff(np.concatenate(([0], active, [0])))
es = np.flatnonzero(da == 1); ee = np.flatnonzero(da == -1) - 1
events = [{"onset": str(np.datetime64(t_tgt[s],'D')), "end": str(np.datetime64(t_tgt[e],'D'))}
          for s, e in zip(es, ee)]
print("active days:", int(active.sum()), "events:", events)

# --- outputs ---
mout = np.zeros((len(t_tgt), int(latm.sum()), int(lonm.sum())), np.uint8)
mout[:, si[:,0], si[:,1]] = mhw
os.makedirs("output", exist_ok=True)
out = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mout)},
    coords={"time": ("time", t_tgt), "lat": ("lat", lat[latm]), "lon": ("lon", lon[lonm])},
)
out.to_netcdf("output/mhw_mask.nc")
report = {
    "region": {"lat_min": 56.63, "lat_max": 57.83, "lon_min": 20.23, "lon_max": 21.43},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2010-06-01", "end": "2010-08-31"},
    "events": events,
    "complete": True,
    "caveats": "None" if int(np.isnan(thrS).sum()) == 0 else "Some smoothed thresholds were NaN where the baseline pool had no finite values.",
}
json.dump(report, open("output/report.json", "w"), indent=2)
print("wrote outputs. total", round(time.time()-t0,1), "s")
