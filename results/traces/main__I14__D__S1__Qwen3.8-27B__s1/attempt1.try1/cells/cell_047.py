import numpy as np, netCDF4, time
from datetime import date, timedelta

t0 = time.time()
nc = netCDF4.Dataset('/work/data/sst_s2.nc', 'r')
a = nc['analysed_sst']
raw = np.asarray(nc['time'][:], dtype=np.float64)
epoch = date(1981,1,1)
secs_per_day = raw / 86400.0
assert (np.abs(secs_per_day - np.round(secs_per_day)) < 1e-6).all()
days = np.round(secs_per_day).astype(int)
dec_dates = np.array([epoch + timedelta(days=int(k)) for k in days])
# full-axis sanity: first/last and a few spot checks
print("first:", dec_dates[0], "last:", dec_dates[-1], "n:", len(dec_dates))
exp_first = date(1982,1,1); exp_last = date(2023,12,31)
assert dec_dates[0] == exp_first and dec_dates[-1] == exp_last
# consecutive
assert (np.diff(days) == 1).all()
print("time axis decoded & consecutive OK")

def tidx(d):
    i = int(np.searchsorted(days, (d - epoch).days))
    assert dec_dates[i] == d, d
    return i

lat_all = nc['latitude'][:].astype(np.float64); lon_all = nc['longitude'][:].astype(np.float64)
lati = np.flatnonzero((lat_all >= 56.13) & (lat_all <= 57.33))
loni = np.flatnonzero((lon_all >= 17.71) & (lon_all <= 18.91))
lat = lat_all[lati]; lon = lon_all[loni]

def dlist(y0, m0, d0_, y1, m1, d1):
    out, d = [], date(y0,m0,d0_)
    e = date(y1,m1,d1)
    while d <= e:
        out.append(d); d += timedelta(days=1)
    return out
base = dlist(1992,1,1,2002,12,31)
target = dlist(2015,6,1,2015,8,31)
b_idx = [tidx(d) for d in base]
t_idx = [tidx(d) for d in target]
print("index mapping verified; base idx", b_idx[0], "..", b_idx[-1], "target idx", t_idx[0], "..", t_idx[-1])

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

si = np.load('/work/data/sea_idx.npy')
thr_s = np.load('/work/data/thr_s.npy')
clim_s = np.load('/work/data/clim_s.npy')
mask = np.load('/work/data/mask.npy')
T = np.load('/work/data/T.npy')
Tsea_full = T[:, si//60, si%60]

cands = np.sort(np.unique(np.append(np.random.default_rng(42).choice(len(si), 6, replace=False), [0, len(si)-1, len(si)//2])))
print("checking cells:", [(int(c), float(lat[si[c]//60]), float(lon[si[c]%60])) for c in cands])

all_ok = True
for c in cands:
    r, cc = si[c]//60, si[c]%60
    SITE_G, FC = int(lati[r]), int(loni[cc])
    col_b = np.asarray(a[b_idx, SITE_G, FC], dtype=np.float64)
    col_t = np.asarray(a[t_idx, SITE_G, FC], dtype=np.float64)
    assert np.isfinite(col_b).all() and np.isfinite(col_t).all(), c
    thr = np.full(366, np.nan); clim = np.full(366, np.nan)
    for doy in range(1, 367):
        if doy == 60: continue
        pool = []
        for j, b in enumerate(base):
            if doy_of(b.month, b.day) == doy:
                pool.append(col_b[j + 5])   # placeholder replaced below
        # do it properly: for each baseline date b_j with doy d, take col_b[j-5 .. j+5]
        pool = []
        for j, b in enumerate(base):
            if doy_of(b.month, b.day) == doy:
                pool.extend(col_b[j-5:j+6])
        pool = np.array(pool)
        assert pool.shape == (121,), (doy, pool.shape)
        thr[doy-1] = hazen_naive(pool)
        clim[doy-1] = pool.mean()
    thr[59] = 0.5*(thr[58]+thr[60]); clim[59] = 0.5*(clim[58]+clim[60])
    thr_sm = np.array([np.mean([thr[(doy+k-1) % 366] for k in range(1, 32)]) for doy in range(1, 367)])
    clim_sm = np.array([np.mean([clim[(doy+k-1) % 366] for k in range(1, 32)]) for doy in range(1, 367)])
    dty = np.array([doy_of(t.month, t.day) for t in target])
    hot = col_t >= thr_sm[dty - 1]
    # MHW (independent implementation)
    m = np.zeros(92, bool); i = 0; ivs = []
    while i < 92:
        if hot[i]:
            j = i
            while j < 92 and hot[j]: j += 1
            if j - i >= 5: ivs.append([i, j-1])
            i = j
        else:
            i += 1
    for s, e in ivs[1:]:
        if s - ivs[-1][1] - 1 <= 2:
            ivs[-1][1] = max(ivs[-1][1], e)
        else:
            ivs.append([s, e])
    for s, e in ivs:
        m[s:e+1] = True
    ok_thr = np.allclose(thr_sm, thr_s[:, c], rtol=0, atol=1e-9)
    ok_clim = np.allclose(clim_sm, clim_s[:, c], rtol=0, atol=1e-9)
    ok_hot = bool(np.array_equal(hot, Tsea_full[:, c] >= thr_s[dty - 1, c]))
    ok_mask = bool(np.array_equal(m, mask[:, c] > 0))
    all_ok &= ok_thr and ok_clim and ok_hot and ok_mask
    print("cell", int(c), "thr:", ok_thr, "clim:", ok_clim, "hot:", ok_hot, "mask:", ok_mask,
          "| max thr diff:", float(np.abs(thr_sm-thr_s[:,c]).max()), "| MHW days:", int(m.sum()))
print("ALL OK:", all_ok, round(time.time()-t0, 1), "s")
nc.close()