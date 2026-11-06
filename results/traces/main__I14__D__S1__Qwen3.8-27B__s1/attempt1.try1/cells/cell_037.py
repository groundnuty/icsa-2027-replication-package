import numpy as np, xarray as xr, json
from datetime import date, timedelta

ds = xr.open_dataset('/work/data/sst_s2.nc', engine="h5netcdf")
tv = ds.time.values
v = ds['analysed_sst']
lat_all = ds['latitude'].values; lon_all = ds['longitude'].values
lati = np.flatnonzero((lat_all >= 56.13) & (lat_all <= 57.33))
loni = np.flatnonzero((lon_all >= 17.71) & (lon_all <= 18.91))
lat = lat_all[lati]; lon = lon_all[loni]
si = np.load('/work/data/sea_idx.npy')
mask = np.load('/work/data/mask.npy')
thr_s = np.load('/work/data/thr_s.npy')
clim_s = np.load('/work/data/clim_s.npy')
tt = np.load('/work/data/tt.npy')
tt_dates = [date.fromisoformat(str(np.datetime64(t))[:10]) for t in tt]
T = np.load('/work/data/T.npy')
Tsea_full = T[:, si//60, si%60]
np.save('/work/data/lati.npy', lati); np.save('/work/data/loni.npy', loni)

def idx_of(d):
    i = int(np.searchsorted(tv, np.datetime64(d.isoformat())))
    assert tv[i] == np.datetime64(d.isoformat())
    return i

ENDS = np.cumsum([31,29,31,30,31,30,31,31,30,31,30,31])
def md_of(doy):
    idx = int(np.searchsorted(ENDS, doy, side='left'))
    return idx+1, doy - (int(ENDS[idx-1]) if idx > 0 else 0)
def doy_of(m, d):
    return d + (int(ENDS[m-2]) if m >= 2 else 0)

def hazen_naive(x, p=0.9):
    x = np.sort(x); n = len(x); h = (n+1)*p
    if h > n: return x[-1]
    lo = int(np.floor(h)); f = h - lo
    return x[lo-1] + f*(x[lo]-x[lo-1]) if lo < n else x[n-1]

def full_chain_for_cell(r, c):
    base = []
    d = date(1992,1,1)
    while d <= date(2002,12,31):
        base.append(d); d += timedelta(days=1)
    thr = np.full(366, np.nan); clim = np.full(366, np.nan)
    SITE_G, FC = lati[r], loni[c]
    cache = {}
    def sst_on(day):
        if day not in cache:
            cache[day] = float(v.values[idx_of(day), SITE_G, FC])
        return cache[day]
    for doy in range(1, 367):
        if doy == 60: continue
        pool = []
        for b in base:
            if doy_of(b.month, b.day) == doy:
                for k in range(-5, 6):
                    pool.append(sst_on(b + timedelta(days=k)))
        pool = np.array(pool, dtype=np.float64)
        assert pool.shape == (121,) and np.isfinite(pool).all(), (doy, np.isfinite(pool).sum())
        thr[doy-1] = hazen_naive(pool)
        clim[doy-1] = pool.mean()
    thr[59] = 0.5*(thr[58]+thr[60]); clim[59] = 0.5*(clim[58]+clim[60])
    thr_sm = np.array([np.mean([thr[(doy+k-1) % 366] for k in range(1, 32)]) for doy in range(1, 367)])
    clim_sm = np.array([np.mean([clim[(doy+k-1) % 366] for k in range(1, 32)]) for doy in range(1, 367)])
    dty = np.array([doy_of(t.month, t.day) for t in tt_dates])
    hot = np.array([float(v.values[idx_of(tt_dates[i].isoformat()), SITE_G, FC]) >= thr_sm[dty[i]-1] for i in range(92)])
    return thr_sm, clim_sm, hot

rng = np.random.default_rng(42)
cands = np.sort(np.unique(np.append(rng.choice(len(si), 6, replace=False), [0, len(si)-1, len(si)//2])))
print("checking cells:", [(int(c), float(lat[si[c]//60]), float(lon[si[c]%60])) for c in cands])
for c in cands:
    r, cc = si[c]//60, si[c]%60
    thr_sm, clim_sm, hot = full_chain_for_cell(r, cc)
    dty = np.array([doy_of(t.month, t.day) for t in tt_dates])
    ok_thr = np.allclose(thr_sm, thr_s[:, c], rtol=0, atol=1e-9)
    ok_clim = np.allclose(clim_sm, clim_s[:, c], rtol=0, atol=1e-9)
    ok_hot = bool(np.array_equal(hot, Tsea_full[:, c] >= thr_s[dty - 1, c]))
    print("cell", int(c), "thr ok:", ok_thr, "clim ok:", ok_clim, "hot ok:", ok_hot,
          " max|thr diff|:", np.abs(thr_sm-thr_s[:,c]).max())