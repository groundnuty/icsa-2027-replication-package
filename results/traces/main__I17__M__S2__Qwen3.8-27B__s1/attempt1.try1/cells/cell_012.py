
import numpy as np, xarray as xr, itertools
X_tgt = np.load("/tmp/X_tgt.npy"); sea2 = np.load("/tmp/sea2.npy")
thrS = np.load("/tmp/thrS.npy"); climS = np.load("/tmp/climS.npy")
ds = xr.open_dataset("/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc", engine="h5netcdf")
t = ds.time.values
t_tgt = t[10378:10470]
si = np.argwhere(sea2); n_sea = si.shape[0]

mlen = [31,29,31,30,31,30,31,31,30,31,30,31]
mdoy = np.zeros((12,31), int)
off=0
for m in range(12):
    mdoy[m,:mlen[m]] = off+1+np.arange(mlen[m]); off += mlen[m]
def md_of(dt):
    mo = int(np.datetime64(dt,'M').astype(np.int64))%12
    day = int(np.datetime64(dt,'D').astype(np.int64)-np.datetime64(np.datetime64(dt,'M'),'D').astype(np.int64))+1
    return mo, day
doy_t = np.array([mdoy[md_of(dt)[0], md_of(dt)[1]-1] for dt in t_tgt])
hot = X_tgt >= thrS[:, doy_t-1].T

def cell_mhw(h):
    out = np.zeros_like(h, bool)
    d = np.diff(np.concatenate(([0], h, [0])))
    s = np.flatnonzero(d==1); e = np.flatnonzero(d==-1)-1
    keep = (e-s+1) >= 5
    cur=None; ivs=[]
    for a,b in zip(s[keep], e[keep]):
        if cur is not None and a-cur[1]-1 <= 2: cur=(cur[0], b)
        else:
            if cur: ivs.append(cur)
            cur=(a,b)
    if cur: ivs.append(cur)
    for a,b in ivs: out[a:b+1]=True
    return out
res = np.stack([cell_mhw(hot[:,c]) for c in range(n_sea)], axis=1)
cnt = res.sum(axis=1)
act = np.where(cnt>0)[0]
print("active day counts series:")
print(" ".join(f"{np.datetime64(t_tgt[i],'D')[5:]}:{int(cnt[i])}" for i in act))

# ---- independent threshold cross-check for 3 cells & several doys ----
X_bas_full = None
reg = ds.analysed_sst.isel(latitude=(ds.latitude>=56.63)&(ds.latitude<=57.83),
                           longitude=(ds.longitude>=20.23)&(ds.longitude<=21.43))
bas = reg.isel(time=slice(3647, 7675)).values.astype("float64")  # 1991-12-27..2003-01-05
Xb = bas[:, si[:,0], si[:,1]]  # (4028, n_sea)

def hazen_manual(vals, p=0.9):
    v = np.sort(vals)
    n = len(v)
    h = n*p + 0.5          # hypothesised numpy 'hazen' position (1-based)
    lo = int(np.floor(h))
    if lo >= n: return v[-1]
    frac = h - lo
    return v[lo-1] + frac*(v[lo]-v[lo-1])

# determine numpy hazen formula empirically
for n in (3, 5, 10, 20, 121):
    v = np.arange(1, n+1, dtype=float)
    q = np.quantile(v, 0.9, method="hazen")
    h = n*0.9 + 0.5
    lo = int(np.floor(h)); frac = h-lo
    pred = v[lo-1] + (v[lo]-v[lo-1])*(frac if lo < n else 0)
    print(n, "numpy", q, "manual(n*.9+.5)", pred, "match", np.isclose(q, pred))

import datetime as dtm
years = list(range(1992,2003))
def pool_dates(d):
    mo, day = (int((d-1)//31+1), 0)
    # invert mdoy
    for m in range(12):
        for dd in range(1, mlen[m]+1):
            if mdoy[m, dd-1] == d:
                mo, day = m+1, dd
    dates = []
    for y in years:
        b = dtm.date(y, mo, day)
        for k in range(-5, 6):
            dates.append(b + dtm.timedelta(days=k))
    return sorted(set(dates))

t_bas = t[3647:7675]
d2idx = {np.datetime64(d): i for i, d in enumerate(t_bas)}

test_cells = [0, 1234, 3303]
test_doys = [153, 180, 200, 244, 365, 1]
maxdiff_thr = 0; maxdiff_clim = 0
for c in test_cells:
    for d in test_doys:
        pd_ = pool_dates(d)
        assert d != 60
        vals = np.array([Xb[d2idx[np.datetime64(x)], c] for x in pd_])
        assert np.isfinite(vals).all() and len(vals) == 121
        thr_man = hazen_manual(vals)
        clim_man = vals.mean()
        # smoothing: mean of days d-15..d+15 of per-day threshold (need per-day thresholds for neighbours!)
        # so first build full per-day thr/clim for this cell manually
        per_d = {}
        for d2 in range(d-15, d+16):
            d2w = ((d2-1) % 366) + 1
            vals2 = np.array([Xb[d2idx[np.datetime64(x)], c] for x in pool_dates(d2w)]) if d2w != 60 else None
            if d2w == 60:
                per_d[d2w] = None  # placeholder, filled below
        per_d[59] = hazen_manual(np.array([Xb[d2idx[np.datetime64(x)], c] for x in pool_dates(59)]))
        per_d[61] = hazen_manual(np.array([Xb[d2idx[np.datetime64(x)], c] for x in pool_dates(61)]))
        per_d[60] = 0.5*(per_d[59]+per_d[61])
        for d2 in range(d-15, d+16):
            d2w = ((d2-1) % 366) + 1
            if d2w not in per_d:
                per_d[d2w] = hazen_manual(np.array([Xb[d2idx[np.datetime64(x)], c] for x in pool_dates(d2w)]))
        sm = np.mean([per_d[((d2-1)%366)+1] for d2 in range(d-15, d+16)])
        idx = d-1
        maxdiff_thr = max(maxdiff_thr, abs(sm - thrS[c, idx]))
        print(f"cell {c} doy {d}: manual {sm:.9f} vs pipeline {thrS[c,idx]:.9f} diff {abs(sm-thrS[c,idx]):.3e}")
print("max smoothing diff:", maxdiff_thr)
