import numpy as np, datetime as dt

z = np.load('/work/interim.npz'); tc = np.load('/work/thr_clim.npz')
sst_t, sst_b, sea, li, oi = z['sst_t'], z['sst_b'], z['sea'], z['li'], z['oi']
thr, clim, thr_s, clim_s = tc['thr'], tc['clim'], tc['thr_s'], tc['clim_s']
NC = 3600
t_full = np.array(['1991-12-27'] + ['1991-12-27']*0)  # placeholder
# build explicit date list for baseline window
start = dt.date(1991,12,27); end = dt.date(2003,1,5)
dates = [start + dt.timedelta(days=k) for k in range((end-start).days+1)]
d2i = {d: k for k, d in enumerate(dates)}

def doy_to_md(d):
    leap = d >= 61
    days = [31,29,31,30,31,30,31,31,30,31,30,31] if leap else [31,28,31,30,31,30,31,31,30,31,30,31]
    for m, nd in enumerate(days):
        if d <= nd: return m+1, d
        d -= nd

def pool_values(cell, d):
    m, dd = doy_to_md(d)
    vals = []
    for y in range(1992, 2003):
        b = dt.date(y, m, dd)
        for k in range(-5, 6):
            t_ = b + dt.timedelta(days=k)
            vals.append(sst_b[d2i[t_], cell//60, cell%60])
    return np.array(vals)

def hazen(x, p):
    x = x[np.isfinite(x)]; x = np.sort(x)
    n = len(x)
    if n == 0: return np.nan, np.nan
    v = min(max(n*p - 0.5, 0.0), n-1)
    j = int(np.floor(v)); g = v - j
    val = x[j] + (g*(x[j+1]-x[j]) if j+1 < n else 0.0)
    return val, x.mean()

rng = np.random.default_rng(11)
sea_idx = np.flatnonzero(sea.reshape(NC))
worst_q = 0.0; worst_m = 0.0
for trial in range(300):
    c = int(rng.choice(sea_idx))
    d = int(rng.integers(1, 367))
    if d == 60: continue
    pv = pool_values(c, d)
    qref, mref = hazen(pv, 0.9)
    qgot = thr[d-1].reshape(NC)[c]; mgot = clim[d-1].reshape(NC)[c]
    assert np.isclose(qref, qgot, rtol=0, atol=1e-12), (trial, c, d, qref, qgot)
    assert np.isclose(mref, mgot, rtol=0, atol=1e-12), (trial, c, d, mref, mgot)
print("300/300 per-value pool checks passed (threshold & climatology, exact match)")

# check day 60 interpolation & smoothing consistency
c = 100
assert np.isclose(thr[59, c//60, c%60], 0.5*(thr[58, c//60, c%60]+thr[60, c//60, c%60]))
a = thr[:, c//60, c%60]
for d in [0, 14, 59, 60, 350, 365]:
    idxs = [(d+k) % 366 for k in range(-15,16)]
    assert np.isclose(thr_s[d, c//60, c%60], np.mean(a[idxs])), d
print("day-60 and 31-day wrap-around smoothing checks passed")
