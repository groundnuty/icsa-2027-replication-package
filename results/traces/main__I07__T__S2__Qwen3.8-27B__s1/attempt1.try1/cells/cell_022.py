
import numpy as np, pandas as pd, time
t0 = time.time()
X = np.load('/tmp/mhw/ext.npy'); Y = np.load('/tmp/mhw/tgt.npy')
ed = pd.to_datetime(np.load('/tmp/mhw/ext_dates.npy'), unit='D')
td = pd.to_datetime(np.load('/tmp/mhw/tgt_dates.npy'), unit='D')
in_mhw_main = np.load('/tmp/mhw/in_mhw.npy')

md = {}
month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
s = 0
for m, L in enumerate(month_days, start=1):
    for dd in range(1, L+1):
        md[(m, dd)] = s + dd
    s += L
def doy2(dateidx):
    return np.array([md[(m, d)] for m, d in zip(np.asarray(dateidx.month), np.asarray(dateidx.day))], dtype=np.int64)
doy_ext = doy2(ed); doy_tgt = doy2(td)

base_mask = (ed >= pd.Timestamp('1992-01-01')) & (ed <= pd.Timestamp('2002-12-31'))
base_idx = np.flatnonzero(base_mask)

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

a = np.arange(1, 21, dtype=float)
print("hazen90 n=20:", hazen90(a.reshape(-1,1))[0,0], "(expect 18.5)")
b = np.arange(1, 21, dtype=float); b[3] = np.nan; b[17] = np.nan
print("hazen90 n=18:", hazen90(b.reshape(-1,1))[0,0], "(expect 18.4)")
print("hazen90 n=1:", hazen90(np.array([[7.5]]))[0,0], "(expect 7.5)")
print("hazen90 n=0:", hazen90(np.array([[np.nan]]))[0,0], "(expect nan)")
print("hazen90 n=5:", hazen90(np.arange(1,6,dtype=float).reshape(-1,1))[0,0], "(expect 5.0)")

C = X.shape[1]
thr = np.full((366, C), np.nan)
minpool = 121
t1 = time.time()
for d in range(1, 367):
    if d == 60: continue
    bs = base_idx[doy_ext[base_idx] == d]
    assert len(bs) == 11
    dates = []
    for b in bs:
        dates.extend(range(int(b)-5, int(b)+6))
    pos = np.array(dates)
    assert len(pos) == 121
    pool = X[pos]
    thr[d-1] = hazen90(pool)
    minpool = min(minpool, int(np.isfinite(pool).sum(axis=0).min()))
print("thr built %.1fs, min pool size over cells: %d" % (time.time()-t1, minpool))
thr[59, :] = 0.5 * (thr[58, :] + thr[60, :])

def smooth31(a):
    n = a.shape[0]
    ext = np.concatenate([a[-15:], a, a[:16]], axis=0)
    out = np.empty_like(a)
    for c0 in range(0, C, 1200):
        blk = ext[:, c0:c0+1200]
        w = np.lib.stride_tricks.sliding_window_view(blk, 31, axis=0)
        v = np.where(np.isfinite(w), w, 0.0)
        cnt = np.isfinite(w).sum(axis=1)
        out[:, c0:c0+1200] = np.where(cnt > 0, v.sum(axis=1) / np.maximum(cnt, 1), np.nan)
    return out
thrS = smooth31(thr)
print("smoothed %.1fs" % (time.time()-t1))

def manual_smooth(a, d):
    return float(np.nanmean(a[(np.arange(d-16, d+15)) % 366]))
for (d, cc) in [(5, 1230), (183, 1230), (366, 3000), (1, 3000), (100, 0)]:
    if not np.isfinite(thr[d-1, cc]):
        continue
    m = manual_smooth(thr[:, cc], d)
    print("smooth chk d=%d c=%d: code %.6f manual %.6f match=%s" % (d, cc, thrS[d-1, cc], m, abs(thrS[d-1, cc]-m) < 1e-12))

with np.errstate(invalid='ignore'):
    hot = (Y >= thrS[doy_tgt-1])
sea = np.isfinite(Y).all(axis=0)
hot = hot & sea[None, :]
T = hot.shape[0]
runlen = np.cumsum(hot, axis=0) - np.flipud(np.cumsum(np.flipud(hot), axis=0)) + 1
runlen = np.where(hot, runlen, 0)
H = hot & (runlen >= 5)
mhw = np.zeros((T, C), bool)
for c in range(C):
    h = H[:, c]
    if not h.any(): continue
    posh = np.flatnonzero(h)
    kp = np.cumsum(h) - 1
    prevp = np.where(kp > 0, posh[np.clip(kp-1, 0, None)], -1)
    nextp = np.where(kp < len(posh), posh[np.clip(kp, 0, None)], -1)
    fill = (~h) & (prevp >= 0) & (nextp >= 0) & (nextp - prevp <= 3)
    mhw[:, c] = h | fill
print("mhw built %.1fs" % (time.time()-t1))

same = bool((mhw.view(np.uint8) == in_mhw_main).all())
print("FULL MASK MATCH:", same)
if not same:
    diff = (mhw.view(np.uint8) != in_mhw_main)
    idx = np.argwhere(diff)
    print("diffs:", len(idx), idx[:10])

act = mhw.any(axis=1)
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
print("regional events (independent):", evs)
np.save('/tmp/mhw/in_mhw_indep.npy', mhw.view(np.uint8))
print("total %.1fs" % (time.time()-t0))
