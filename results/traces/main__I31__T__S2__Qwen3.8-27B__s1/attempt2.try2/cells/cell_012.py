import numpy as np, json, os, time
from datetime import date, timedelta
T0 = time.time()

z = np.load('/work/read_done.npz', allow_pickle=False)
base = z['base']                      # (4028, 60, 60) float32
tgt  = z['tgt']                       # (92, 60, 60) float32
lat_vals = z['lat_vals']; lon_vals = z['lon_vals']
b_dates = z['b_dates']; t_dates = z['t_dates']
nB, La, Lo = base.shape
C = La * Lo
print("loaded", base.shape, tgt.shape)

# ---------- self-test: vectorized per-row hazen nanquantile ----------
def nanquantile_hazen_rows(X):
    X = np.ascontiguousarray(X, dtype=np.float64)
    C, M = X.shape
    nan = np.isnan(X)
    n = M - nan.sum(axis=1)                       # valid counts
    Xs = np.sort(np.where(nan, np.inf, X), axis=1)
    h = (n + 1) * 0.9 - 1.0
    j = np.floor(h).astype(np.int64)
    j = np.clip(j, 0, np.maximum(n - 1, 0))
    g = h - j
    rows = np.arange(C)
    v1 = Xs[rows, j]
    jj2 = np.minimum(j + 1, np.maximum(n - 1, 0))
    v2 = Xs[rows, jj2]
    use = (g > 0) & (j + 1 < n)
    res = np.where(use, v1 + g * (v2 - v1), v1)
    res = np.where(n > 0, res, np.nan)
    return res

rng = np.random.default_rng(0)
Xt = rng.normal(300, 5, (5000, 121))
Xt[rng.random(Xt.shape) < 0.08] = np.nan
Xt[0] = np.nan; Xt[1] = np.nan; Xt[2] = np.nan; Xt[2] = Xt[2].copy()  # row2 all nan
Xt[3] = np.nan; Xt[3, :5] = rng.normal(300, 5, 5)                      # row3 one valid
ref = np.array([np.quantile(Xt[r][~np.isnan(Xt[r])], 0.9, method='hazen') if np.isfinite(Xt[r]).any() else np.nan for r in range(Xt.shape[0])])
got = nanquantile_hazen_rows(Xt)
mask = ~(np.isnan(ref) & np.isnan(got))
print("quantile self-test max abs diff:", np.nanmax(np.abs(got[mask] - ref[mask])))

def smooth31(a):
    a = np.asarray(a, dtype=np.float64)
    A = np.concatenate([a, a, a])
    cs = np.cumsum(np.concatenate([[0.0], A]))
    return (cs[382:748] - cs[351:717]) / 31.0
ar = rng.random(366)
ref_s = np.array([ar[(d + np.arange(-15, 16)) % 366].mean() for d in range(366)])
print("smoothing self-test max abs diff:", np.abs(smooth31(ar) - ref_s).max())

# ---------- day-of-year machinery ----------
doy_to_md = np.zeros((367, 2), dtype=int)
for d in range(1, 367):
    dt = date(2000, 1, 1) + timedelta(days=d - 1)
    doy_to_md[d] = (dt.month, dt.day)
base_py = [np.datetime64(d) for d in b_dates]
date_to_bidx = {np.datetime64(d): k for k, d in enumerate(b_dates)}
bidx_dates = {k: base_py[k] for k in range(nB)}
years = list(range(1992, 2003))
doy_b = np.array([base_py[k].astype(object).timetuple().tm_yday for k in range(nB)], dtype=np.int32)
print("base slice doy range:", doy_b.min(), doy_b.max())

thr  = np.full((C, 366), np.nan)
clim = np.full((C, 366), np.nan)
pool_sizes = {}
for d in range(1, 367):
    if d == 60:
        continue
    m, dd = doy_to_md[d]
    wset = set()
    for y in years:
        b = date(y, m, dd)
        for k in range(-5, 6):
            t64 = np.datetime64(b + timedelta(days=k), 'D')
            ki = date_to_bidx.get(t64)
            if ki is not None:
                wset.add(ki)
    mask = np.zeros(nB, bool); mask[np.fromiter(wset, dtype=np.int64)] = True
    X = base[mask].reshape(len(wset), C).T.astype(np.float64)   # (C, nwin)
    thr[:, d] = nanquantile_hazen_rows(X)
    nn = ~np.isnan(X)
    s = np.where(nn, X, 0.0).sum(axis=1)
    clim[:, d] = np.where(nn.sum(axis=1) > 0, s / np.maximum(nn.sum(axis=1), 1), np.nan)
    pool_sizes[d] = len(wset)
assert len(set(pool_sizes.values())) == 1, "unexpected pool size variation"
print("pool size (dates) per doy:", list(pool_sizes.values())[0], " elapsed:", time.time()-T0)

# day 60 = mean of days 59 and 61
thr[:, 60] = np.mean(thr[:, [59, 61]], axis=1)
clim[:, 60] = np.mean(clim[:, [59, 61]], axis=1)

# 31-day wrap-around centred moving mean, per cell
thr  = np.array([smooth31(thr[c])  for c in range(C)])
clim = np.array([smooth31(clim[c]) for c in range(C)])
print("thr range:", np.nanmin(thr), np.nanmax(thr), " clim range:", np.nanmin(clim), np.nanmax(clim))
print("cells with any NaN thr:", np.isnan(thr).any(axis=1).sum())

np.savez('/work/stats.npz', thr=thr, clim=clim,
         lat_vals=lat_vals, lon_vals=lon_vals,
         b_dates=b_dates, t_dates=t_dates)
print("stats saved, elapsed:", time.time()-T0)
