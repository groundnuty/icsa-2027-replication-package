vscript = r'''
import numpy as np, xarray as xr, datetime as dt

# ---------- reload data (same extraction) ----------
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
times = ds['time'].values.astype('datetime64[D]')
lat = ds['latitude'].values; lon = ds['longitude'].values
latm = (lat >= 61.57 - 1e-5) & (lat <= 62.77 + 1e-5)
lonm = (lon >= 20.17 - 1e-5) & (lon <= 21.37 + 1e-5)
li, lo = np.where(latm)[0], np.where(lonm)[0]
def tidx(d): return int(np.searchsorted(times, np.datetime64(d, 'D')))
t0b, t1b = tidx('1991-12-27'), tidx('2003-01-05')
t0t, t1t = tidx('2021-06-01'), tidx('2021-08-31')
Xw = ds['analysed_sst'].isel(time=slice(t0b, t1b+1), latitude=li, longitude=lo).values.astype(np.float64)
Xt = ds['analysed_sst'].isel(time=slice(t0t, t1t+1), latitude=li, longitude=lo).values.astype(np.float64)
ds.close()
C = len(li)*len(lo)
Xw = Xw.reshape(-1, C); Xt = Xt.reshape(-1, C)
T = Xw.shape[0]

# ---------- doy by month/day (pure python) ----------
def doy_py(d):  # d: datetime.date
    leapcal = [31,29,31,30,31,30,31,31,30,31,30,31]
    cum = 0
    for m in range(d.month-1):
        cum += leapcal[m]
    return cum + d.day

# ---------- independent pool construction (pure python dates) ----------
wstart = dt.date(1991,12,27)
wlen = T
def widx(d): return (d - wstart).days
wdates = [wstart + dt.timedelta(days=i) for i in range(wlen)]
assert widx(wdates[0]) == 0 and wdates[-1] == dt.date(2003,1,5)
baseline = [dt.date(1992,1,1) + dt.timedelta(days=i) for i in range(4018)]
assert baseline[0] == dt.date(1992,1,1) and baseline[-1] == dt.date(2002,12,31)
assert all(widx(b) for b in [baseline[0], baseline[-1]])

def pool_dates(doyval):
    qs = [b for b in baseline if doy_py(b) == doyval]
    dates = set()
    for q in qs:
        for k in range(-5,6):
            dates.add(q + dt.timedelta(days=k))
    return sorted(dates), len(qs)

def hazen_manual(vals_sorted, p):
    # 1-based virtual index v = n*p + 0.5, clamped to [1, n]
    n = len(vals_sorted)
    if n == 0: return float('nan')
    v = n*p + 0.5
    if v <= 1: return float(vals_sorted[0])
    if v >= n: return float(vals_sorted[-1])
    j = int(np.floor(v)); g = v - j
    return (1-g)*float(vals_sorted[j-1]) + g*float(vals_sorted[j])

# ---------- property test manual hazen vs numpy ----------
rng = np.random.default_rng(0)
ok = True
for trial in range(300):
    n = int(rng.integers(1, 140))
    a = rng.normal(size=n)
    q = float(rng.random())
    mn = hazen_manual(np.sort(a), q)
    nn = np.quantile(a, q, method='hazen')
    if abs(mn - nn) > 1e-9*max(1,abs(nn)):
        ok = False; print("MISMATCH hazen", n, q, mn, nn); break
# with NaNs
for trial in range(200):
    n = int(rng.integers(1, 140))
    a = rng.normal(size=n)
    a[rng.random(n) < 0.2] = np.nan
    a = a[~np.isnan(a)]
    if len(a) == 0: continue
    q = float(rng.random())
    mn = hazen_manual(np.sort(a), q)
    nn = np.nanquantile(np.sort(a), q, method='hazen') if len(a) else float('nan')
    if abs(mn - nn) > 1e-9*max(1,abs(nn)):
        ok = False; print("MISMATCH nanhazen", len(a), q, mn, nn); break
print("hazen manual == numpy hazen:", ok)

# ---------- vectorized pipeline-style recompute (independent of M-matrix approach) ----------
# Build pools by per-doy date lists, vectorised over cells
import collections
doy_lists = {}
for d in range(1, 367):
    if d == 60: continue
    ds_, nq = pool_dates(d)
    assert nq == 11, (d, nq)
    idxs = [widx(x) for x in ds_]
    assert len(set(idxs)) == 121 and all(0 <= i < T for i in idxs)
    doy_lists[d] = np.array(idxs)
print("pool date counts ok (121 each, unique)")

thr2 = np.full((366, C), np.nan); clim2 = np.full((366, C), np.nan)
for d in range(1, 367):
    if d == 60: continue
    V = Xw[doy_lists[d], :]
    finite = ~np.isnan(V)
    nf = finite.sum(axis=0)
    m = np.where(finite, V, 0.0).sum(axis=0)
    clim2[d-1] = np.where(nf > 0, m / np.where(nf > 0, nf, 1), np.nan)
    # hazen quantile: sort (NaNs last), v = nf*0.9 + 0.5 (1-based)
    S = np.sort(V, axis=0)
    v = nf*0.9 + 0.5
    j = np.clip(np.floor(v).astype(int), 1, np.maximum(nf, 1))
    g = v - np.floor(v)
    a1 = S[j-1, np.arange(C)]
    a2 = np.where(j < nf, S[j, np.arange(C)], S[j-1, np.arange(C)])
    thr2[d-1] = np.where(nf > 0, (1-g)*a1 + g*a2, np.nan)
thr2[59] = 0.5*(thr2[58] + thr2[60]); clim2[59] = 0.5*(clim2[58] + clim2[60])

def smooth366(A):
    Af = np.where(np.isnan(A), 0.0, A); Cf = (~np.isnan(A)).astype(np.float64)
    S = np.zeros_like(A); N = np.zeros_like(A)
    for k in range(-15,16):
        S += np.roll(Af, -k, axis=0); N += np.roll(Cf, -k, axis=0)
    out = np.full_like(A, np.nan); nz = N > 0
    out[nz] = S[nz]/N[nz]; return out
thr2s = smooth366(thr2)

# ---------- brute force check for sampled cells & doys ----------
sea = np.isfinite(Xt).all(axis=0)
cells = [int(c) for c in np.where(sea)[0]]
sample_cells = cells[::max(1, len(cells)//12)] + [cells[-1]]
sample_d = [1, 2, 59, 61, 100, 153, 200, 244, 300, 365, 366]
maxdiff_q = 0.0; maxdiff_c = 0.0; bad = []
for c in sample_cells:
    for d in sample_d:
        ds_, _ = pool_dates(d)
        vals = [Xw[widx(x), c] for x in ds_]
        vals = [v for v in vals if np.isfinite(v)]
        vals.sort()
        q = hazen_manual(vals, 0.9)
        cm = float(np.mean(vals)) if vals else float('nan')
        dq = abs(q - thr2[d-1, c]) if np.isfinite(thr2[d-1,c]) else float('nan')
        dc = abs(cm - clim2[d-1, c]) if np.isfinite(clim2[d-1,c]) else float('nan')
        if not (np.isclose(dq, 0, atol=1e-9) and np.isclose(dc, 0, atol=1e-9)):
            bad.append((c, d, q, thr2[d-1,c], cm, clim2[d-1,c]))
        maxdiff_q = max(maxdiff_q, dq if np.isfinite(dq) else 0)
        maxdiff_c = max(maxdiff_c, dc if np.isfinite(dc) else 0)
print("brute-force vs vectorized: n_bad =", len(bad), "max|dq| =", maxdiff_q, "max|dc| =", maxdiff_c)
for b in bad[:5]: print("BAD:", b)

# smoothing spot check: direct window means
maxdiff_s = 0.0
for c in sample_cells[:4]:
    for d in [58, 59, 60, 152, 200]:
        w = [thr2[(d + k) % 366, c] for k in range(-15, 16)]
        ref = float(np.mean(w))
        got = thr2s[d, c]
        maxdiff_s = max(maxdiff_s, abs(ref - got))
print("smoothing spot max diff:", maxdiff_s)

# day-60 rule check
print("day60 rule ok:", np.allclose(thr2[59], 0.5*(thr2[58]+thr2[60]), equal_nan=True),
      np.allclose(clim2[59], 0.5*(clim2[58]+clim2[60]), equal_nan=True))

# save independent thr for next stage
np.save('/work/thr2s.npy', thr2s)
np.save('/work/sea.npy', sea)
np.save('/work/Xt.npy', Xt)
np.save('/work/tdoy.npy', np.array([doy_py(np.datetime_as_string(times[t0t+i], unit='D') and dt.date.fromisoformat(np.datetime_as_string(times[t0t+i], unit='D'))) for i in range(92)]))
print("saved intermediates")
'''
open('/work/verify1.py','w').write(vscript)
print("verify1 written")
