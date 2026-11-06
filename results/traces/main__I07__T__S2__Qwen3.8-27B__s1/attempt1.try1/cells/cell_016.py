
import numpy as np, pandas as pd
X = np.load('/tmp/mhw/ext.npy'); Y = np.load('/tmp/mhw/tgt.npy')
ed = pd.to_datetime(np.load('/tmp/mhw/ext_dates.npy'), unit='D')
td = pd.to_datetime(np.load('/tmp/mhw/tgt_dates.npy'), unit='D')
in_mhw = np.load('/tmp/mhw/in_mhw.npy')

# recreate thr (pre-smoothing) for spot checks, independent code path
cum = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
doy_ext = cum[np.asarray(ed.month)-1] + np.asarray(ed.day)
def hf5(x, p):
    x = np.sort(x); n = len(x)
    h = (np.arange(1, n+1) - 0.5) / n
    return float(np.interp(p, h, x))

# pick a definitely-sea cell
sea = np.isfinite(Y).all(axis=0)
c = 1230
print("cell", c, "is sea:", bool(sea[c]), "lat idx/lon idx:", c//60, c%60)

# independent pool for doy 183 (Jul 1): baseline Jul 1 dates 1992..2002, +/-5 days
idx_of = {d: i for i, d in enumerate(ed)}
pools = []
for yr in range(1992, 2003):
    b = pd.Timestamp(yr, 7, 1)
    for k in range(-5, 6):
        pools.append(idx_of[b + pd.Timedelta(days=k)])
vals = X[pools, c]
vals = vals[np.isfinite(vals)]
q_manual = hf5(vals, 0.9)
m_manual = float(np.mean(vals))
# recompute thr[182, c] the same way as main run
b0, b1 = 5, 4023
pos = np.concatenate([np.arange(p0-5, p0+6) for p0 in (b0 + np.flatnonzero(doy_ext[b0:b1] == 183))])
print("n pool dates:", len(pos), "same date set:", set(pos.tolist()) == set(pools))
v2 = X[pos, c]; v2 = v2[np.isfinite(v2)]
print("manual hazen q0.9:", q_manual, "recomputed:", hf5(v2, 0.9), "mean:", m_manual)

# smoothing check: thrS[182] = mean of thr[168..198] (mod 366)
# recompute full thr array quickly for the one cell (independent, per-column)
thr_c = np.full(366, np.nan)
with np.errstate(all='ignore'):
    for d in range(1, 367):
        if d == 60: continue
        p = b0 + np.flatnonzero(doy_ext[b0:b1] == d)
        pp = np.concatenate([np.arange(p0-5, p0+6) for p0 in p])
        v = X[pp, c]; v = v[np.isfinite(v)]
        thr_c[d-1] = hf5(v, 0.9) if len(v) else np.nan
thr_c[59] = 0.5*(thr_c[58] + thr_c[60])
sm_manual = float(np.nanmean(thr_c[(np.arange(183-15, 183+16)) % 366]))
print("smoothed thr at Jul1 (manual):", sm_manual)

# compare with the saved in_mhw: recompute hot days for this cell using thr_c
Yc = Y[:, c]
doys = cum[np.asarray(td.month)-1] + np.asarray(td.day)
# main run's thrS is not saved; reconstruct main-run thrS for this cell by rerunning loop is costly;
# instead verify the saved in_mhw is consistent with thr_c-based hot days (should match exactly)
hot_c = Yc >= sm_check := np.array([float(np.nanmean(thr_c[(np.arange(d-15, d+16)) % 366])) for d in doys])
mhw_ref = (in_mhw[:, c] == 1)
# derive expected mhw from hot_c with same 5-day/2-gap rule
col = hot_c
runs = []
i = 0
T = len(col)
while i < T:
    if col[i]:
        j = i
        while j < T and col[j]: j += 1
        if j - i >= 5: runs.append([i, j])
        i = j
    else: i += 1
merged = []
for s, e in runs:
    if merged and s - merged[-1][1] <= 2: merged[-1][1] = e
    else: merged.append([s, e])
exp = np.zeros(T, bool)
for s, e in merged: exp[s:e] = True
print("per-cell MHW match:", bool((exp == mhw_ref).all()), "| in-MHW days:", int(mhw_ref.sum()))
# hot-day pattern for this cell
print("hot run days in period:", int(col.sum()))
ev = [(str(td[s].date()), str(td[e-1].date())) for s, e in merged]
print("this cell's merged events:", ev)
