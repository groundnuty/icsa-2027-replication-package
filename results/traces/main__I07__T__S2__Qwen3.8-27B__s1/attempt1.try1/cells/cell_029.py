
import numpy as np, pandas as pd, time
t0 = time.time()
X = np.load('/tmp/mhw/ext.npy'); Y = np.load('/tmp/mhw/tgt.npy')
td = pd.to_datetime(np.load('/tmp/mhw/tgt_dates.npy'), unit='D')
ed = pd.to_datetime(np.load('/tmp/mhw/ext_dates.npy'), unit='D')
in_mhw_main = np.load('/tmp/mhw/in_mhw.npy')
cum = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
doy_ext = cum[np.asarray(ed.month)-1] + np.asarray(ed.day)
doy_tgt = cum[np.asarray(td.month)-1] + np.asarray(td.day)
C = Y.shape[1]; T = 92
b0, b1 = 5, 4023

def hazen90(pool):
    p = np.where(np.isnan(pool), np.inf, pool)
    p = np.sort(p, axis=0)
    rows = p.shape[0]
    n = (p < np.inf).sum(axis=0)
    n1 = np.where(n == 0, 1, n).astype(np.float64)
    ifl = 0.9 * n1 + 0.5
    lo = np.clip(np.floor(ifl).astype(np.int64), 1, rows)
    frac = (ifl - lo).astype(np.float64)
    x1 = np.take_along_axis(p, (lo-1)[None, :], axis=0)
    x2idx = np.minimum(np.minimum(lo, np.where(n == 0, 1, n - 1)), rows - 1).astype(np.int64)
    x2 = np.take_along_axis(p, x2idx[None, :], axis=0)
    out = x1 + frac * (x2 - x1)
    return np.where(n == 0, np.nan, out)

thr = np.full((366, C), np.nan)
for d in range(1, 367):
    if d == 60: continue
    p = b0 + np.flatnonzero(doy_ext[b0:b1] == d)
    thr[d-1] = hazen90(X[np.concatenate([np.arange(p0-5, p0+6) for p0 in p])])
thr[59] = 0.5*(thr[58] + thr[60])
idxm = (np.arange(366)[:, None] + np.arange(-15, 16)[None, :]) % 366
thrS = np.empty_like(thr)
for c0 in range(0, C, 1200):
    v = thr[idxm][:, :, c0:c0+1200]
    valid = np.isfinite(v)
    thrS[:, c0:c0+1200] = np.where(valid.sum(axis=1) > 0,
        np.sum(np.where(valid, v, 0.0), axis=1) / np.maximum(valid.sum(axis=1), 1), np.nan)
print("thr+smooth %.1fs" % (time.time()-t0))

with np.errstate(invalid='ignore'):
    hot = (Y >= thrS[doy_tgt-1])
sea = np.isfinite(Y).all(axis=0)

# THIRD method: iterative merge, inclusive indices, written differently
def mhw_cell(h):
    T = len(h)
    runs = []
    i = 0
    while i < T:
        if h[i]:
            j = i
            while j < T and h[j]:
                j += 1
            if j - i >= 5:
                runs.append([i, j-1])
            i = j
        else:
            i += 1
    merged = True
    while merged:
        merged = False
        i = 0
        while i < len(runs) - 1:
            if runs[i+1][0] - runs[i][1] - 1 <= 2:
                runs[i][1] = runs[i+1][1]
                runs.pop(i+1)
                merged = True
            else:
                i += 1
    out = np.zeros(T, bool)
    for s, e in runs:
        out[s:e+1] = True
    return out

mhw3 = np.zeros((T, C), bool)
for c in range(C):
    mhw3[:, c] = mhw_cell(hot[:, c] and sea[c] if False else (hot[:, c] & sea[c]))
print("third method %.1fs" % (time.time()-t0))

print("main == third:", bool((in_mhw_main == mhw3.view(np.uint8)).all()))
# also confirm the runlen-bug diagnosis: recompute the buggy indep mhw quickly? skip; just report
act = mhw3.any(axis=1)
evs = []
i = 0
while i < T:
    if act[i]:
        j = i
        while j < T and act[j]: j += 1
        evs.append((str(td[i].date()), str(td[j-1].date()), j-i))
        i = j
    else:
        i += 1
print("regional events (third method):", evs)
print("active days:", int(act.sum()))
print("total %.1fs" % (time.time()-t0))
