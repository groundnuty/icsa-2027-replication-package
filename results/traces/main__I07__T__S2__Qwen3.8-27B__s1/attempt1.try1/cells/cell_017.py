
import numpy as np, pandas as pd
X = np.load('/tmp/mhw/ext.npy'); Y = np.load('/tmp/mhw/tgt.npy')
ed = pd.to_datetime(np.load('/tmp/mhw/ext_dates.npy'), unit='D')
td = pd.to_datetime(np.load('/tmp/mhw/tgt_dates.npy'), unit='D')
in_mhw = np.load('/tmp/mhw/in_mhw.npy')

cum = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
doy_ext = cum[np.asarray(ed.month)-1] + np.asarray(ed.day)
def hf5(x, p):
    x = np.sort(x); n = len(x)
    h = (np.arange(1, n+1) - 0.5) / n
    return float(np.interp(p, h, x))

sea = np.isfinite(Y).all(axis=0)
c = 1230
print("cell", c, "is sea:", bool(sea[c]), "lat/lon idx:", c//60, c%60)

idx_of = {d: i for i, d in enumerate(ed)}
pools = []
for yr in range(1992, 2003):
    b = pd.Timestamp(yr, 7, 1)
    for k in range(-5, 6):
        pools.append(idx_of[b + pd.Timedelta(days=k)])
b0, b1 = 5, 4023
pos = np.concatenate([np.arange(p0-5, p0+6) for p0 in (b0 + np.flatnonzero(doy_ext[b0:b1] == 183))])
print("n pool dates:", len(pos), "same date set as manual:", set(pos.tolist()) == set(pools))
vals = X[pos, c]; vals = vals[np.isfinite(vals)]
print("manual hazen q0.9 (doy183):", hf5(vals, 0.9), " mean:", float(np.mean(vals)))

thr_c = np.full(366, np.nan)
with np.errstate(all='ignore'):
    for d in range(1, 367):
        if d == 60: continue
        p = b0 + np.flatnonzero(doy_ext[b0:b1] == d)
        pp = np.concatenate([np.arange(p0-5, p0+6) for p0 in p])
        v = X[pp, c]; v = v[np.isfinite(v)]
        thr_c[d-1] = hf5(v, 0.9) if len(v) else np.nan
thr_c[59] = 0.5*(thr_c[58] + thr_c[60])
sm183 = float(np.nanmean(thr_c[np.arange(168, 198) % 366]))
print("smoothed thr at doy183 (manual):", sm183)
# wrap-around test: doy 5 window should use days 356..20
sm5 = float(np.nanmean(thr_c[(np.arange(5-15, 5+16)) % 366]))
manual5 = float(np.nanmean(np.concatenate([thr_c[351:366], thr_c[0:20]])))
print("wrap check doy5:", sm5, manual5, "match:", sm5 == manual5)

Yc = Y[:, c]
doys = cum[np.asarray(td.month)-1] + np.asarray(td.day)
thrS_c = np.array([float(np.nanmean(thr_c[(np.arange(d-15, d+16)) % 366])) for d in doys])
hot_c = Yc >= thrS_c
runs = []
i = 0; T = len(hot_c)
while i < T:
    if hot_c[i]:
        j = i
        while j < T and hot_c[j]: j += 1
        if j - i >= 5: runs.append([i, j])
        i = j
    else: i += 1
merged = []
for s, e in runs:
    if merged and s - merged[-1][1] <= 2: merged[-1][1] = e
    else: merged.append([s, e])
exp = np.zeros(T, bool)
for s, e in merged: exp[s:e] = True
mhw_ref = (in_mhw[:, c] == 1)
print("per-cell MHW match:", bool((exp == mhw_ref).all()), "| in-MHW days:", int(mhw_ref.sum()))
print("this cell's merged events:", [(str(td[s].date()), str(td[e-1].date()), e-s) for s, e in merged])
print("raw hot runs:", [(str(td[s].date()), str(td[e-1].date()), e-s) for s, e in runs])
