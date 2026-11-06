
import numpy as np, pandas as pd, time, json, os
t0 = time.time()
X = np.load('/tmp/mhw/ext.npy')          # (4028, 3600)
Y = np.load('/tmp/mhw/tgt.npy')          # (92, 3600)
ed = pd.to_datetime(np.load('/tmp/mhw/ext_dates.npy'), unit='D')
td = pd.to_datetime(np.load('/tmp/mhw/tgt_dates.npy'), unit='D')
lat = np.load('/tmp/mhw/lat.npy'); lon = np.load('/tmp/mhw/lon.npy')
print("ext:", ed[0].date(), ed[-1].date(), len(ed), "| tgt:", td[0].date(), td[-1].date(), len(td))
assert str(ed[0].date()) == '1991-12-27' and str(ed[-1].date()) == '2003-01-05'
assert str(td[0].date()) == '2021-06-01' and str(td[-1].date()) == '2021-08-31'

doy_ext = ed.dayofyear.values.astype(np.int64)      # 1..366 (60 only in leap years)
doy_tgt = td.dayofyear.values.astype(np.int64)
C = X.shape[1]
print("doy tgt min/max:", doy_tgt.min(), doy_tgt.max())

# baseline positions: 1992-01-01 .. 2002-12-31 -> ext idx 5..4022
b0, b1 = 5, 4023
bas_doy = doy_ext[b0:b1]
assert (bas_doy == np.array([np.datetime64(d).astype('int') for d in []]) or True)
# check pool construction sizes
pos_by_d = {}
for d in range(1, 367):
    if d == 60:
        continue
    p = b0 + np.flatnonzero(bas_doy == d)
    assert len(p) == 11, (d, len(p))
    pos = np.concatenate([np.arange(p0-5, p0+6) for p0 in p])
    assert len(pos) == 121 and pos.min() >= 0 and pos.max() < X.shape[0]
    pos_by_d[d] = pos

# quick sanity: hazen quantile & nan behavior
a = np.arange(1, 21, dtype=float)
print("hazen check:", np.quantile(a, 0.9, method='hazen'), "(expect 18.5)")
allnan = np.full((121, 3), np.nan)
with np.errstate(all='ignore'):
    q = np.quantile(allnan, 0.9, axis=0, method='hazen', nan_policy='omit')
print("all-NaN quantile:", q)

thr = np.full((366, C), np.nan); clim = np.full((366, C), np.nan)
t1 = time.time()
with np.errstate(all='ignore'):
    for d in range(1, 367):
        if d == 60:
            continue
        pool = X[pos_by_d[d]]                      # (121, C)
        thr[d-1] = np.quantile(pool, 0.9, axis=0, method='hazen', nan_policy='omit')
        clim[d-1] = np.nanmean(pool, axis=0)
print("pools done: %.1fs" % (time.time()-t1))
# day 60 = mean of days 59 and 61
thr[59] = 0.5*(thr[58] + thr[60]); clim[59] = 0.5*(clim[58] + clim[60])

def circ_smooth31(a):
    n = a.shape[0]
    assert n == 366
    idx = (np.arange(n)[:, None] + np.arange(-15, 16)[None, :]) % n     # (366,31)
    out = np.empty_like(a)
    for c0 in range(0, C, 1200):
        v = a[idx][:, :, c0:c0+1200]
        valid = np.isfinite(v)
        s = np.sum(np.where(valid, v, 0.0), axis=1)
        cnt = valid.sum(axis=1)
        out[:, c0:c0+1200] = np.where(cnt > 0, s / np.maximum(cnt, 1), np.nan)
    return out

t1 = time.time()
thrS = circ_smooth31(thr); climS = circ_smooth31(clim)
print("smoothing done: %.1fs" % (time.time()-t1))

# sea cells: finite on every target day
sea = np.isfinite(Y).all(axis=0)
print("sea cells:", int(sea.sum()), "of", C)

hot = Y >= thrS[doy_tgt - 1]          # (92, C); NaN comparisons -> False
with np.errstate(invalid='ignore'):
    hot = np.where(sea[None, :], hot, False)
print("hot days total:", int(hot.sum()))

# per-cell MHWs: runs >= 5, join gaps of 1-2
T = 92
in_mhw = np.zeros((T, C), np.uint8)
for c in range(C):
    col = hot[:, c]
    if not col.any():
        continue
    runs = []
    i = 0
    while i < T:
        if col[i]:
            j = i
            while j < T and col[j]:
                j += 1
            if j - i >= 5:
                runs.append([i, j])
            i = j
        else:
            i += 1
    merged = []
    for s, e in runs:
        if merged and s - merged[-1][1] <= 2:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    for s, e in merged:
        in_mhw[s:e, c] = 1

active = in_mhw.any(axis=1)
print("active days:", int(active.sum()), "of", T)
evs = []
i = 0
while i < T:
    if active[i]:
        j = i
        while j < T and active[j]:
            j += 1
        evs.append((str(td[i].date()), str(td[j-1].date()), j - i))
        i = j
    else:
        i += 1
print("regional events:", len(evs))
for e in evs:
    print("  %s .. %s (%d days)" % e)

np.save('/tmp/mhw/in_mhw.npy', in_mhw)
np.save('/tmp/mhw/events.npy', np.array(evs, dtype=object) if evs else np.array([], dtype=object))
print("compute total: %.1fs" % (time.time()-t0))
