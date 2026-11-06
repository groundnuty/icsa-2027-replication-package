
import numpy as np, pandas as pd, time
t0 = time.time()
X = np.load('/tmp/mhw/ext.npy'); Y = np.load('/tmp/mhw/tgt.npy')
ed = pd.to_datetime(np.load('/tmp/mhw/ext_dates.npy'), unit='D')
td = pd.to_datetime(np.load('/tmp/mhw/tgt_dates.npy'), unit='D')
in_mhw_main = np.load('/tmp/mhw/in_mhw.npy')

# --- independent doy mapping via explicit dict (different from cum-array method)
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
assert doy_ext.max() == 366 and doy_ext.min() == 1
print("tgt doys:", doy_tgt.min(), "..", doy_tgt.max())

# --- baseline positions derived by date, not index constants
base_mask = (ed >= pd.Timestamp('1992-01-01')) & (ed <= pd.Timestamp('2002-12-31'))
base_idx = np.flatnonzero(base_mask)
print("baseline n:", len(base_idx), base_idx[0], base_idx[-1])

# --- independent hazen-0.9 for a (121, C) pool via sort+interp (no pandas, no np.quantile)
def hazen90(pool):
    # replace NaN with +inf so valid values sort first
    p = np.where(np.isnan(pool), np.inf, pool)
    p = np.sort(p, axis=0)                      # (121, C)
    n = (p < np.inf).sum(axis=0).astype(np.float64)
    n = np.where(n == 0, 1, n)
    h = (np.arange(1, 122) - 0.5) / 121.0       # rank positions if n=121
    # per-column: i_float = 0.9*n + 0.5
    ifl = 0.9 * n + 0.5
    lo = np.floor(ifl).astype(int)              # 1-based rank of lower point
    frac = ifl - lo
    x1 = np.take_along_axis(p, (lo-1)[:, None] if False else (lo-1)[None, :], axis=0)
    ok = (lo <= 121) & (frac > 0) & (lo <= 121)
    # upper point only when frac>0 and lo <= 119? hazen: max h at rank n is (n-0.5)/n < 1, so lo <= n always; upper rank lo+1 <= n when frac>0
    x2 = np.take_along_axis(p, np.minimum(lo, 121)[None, :], axis=0)
    out = x1 + frac * (x2 - x1)
    out = np.where((frac > 0) & (lo < n), out, x1)   # when upper rank exceeds n, use lower
    out = np.where(n == 0, np.nan, out)
    return out

# quick unit tests of hazen90
a = np.arange(1, 21, dtype=float)
print("hazen90 n=20:", hazen90(a[None, :].T if False else a.reshape(-1,1))[0,0], "(expect 18.5)")
b = np.arange(1, 21, dtype=float); b[3] = np.nan; b[17] = np.nan
print("hazen90 n=18:", hazen90(b.reshape(-1,1))[0,0])
print("hazen90 n=1:", hazen90(np.array([[7.5]]))[0,0])

# --- build thresholds, day 60 fill, smoothing (different implementation style)
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
    minpool = min(minpool, int((np.isfinite(pool)).sum(axis=0).min()))
print("thr built %.1fs, min pool size over cells: %d" % (time.time()-t1, minpool))
thr[59, :] = 0.5 * (thr[58, :] + thr[60, :])

# smoothing: pad-circular + sliding_window_view (different from index-matrix gather)
def smooth31(a):
    n = a.shape[0]
    ext = np.concatenate([a[-15:], a, a[:16]], axis=0)   # (412, C)
    out = np.empty_like(a)
    for c0 in range(0, C, 1200):
        blk = ext[:, c0:c0+1200]
        w = np.lib.stride_tricks.sliding_window_view(blk, 31, axis=0)  # (382, 31, chunk)
        v = np.where(np.isfinite(w), w, 0.0)
        cnt = np.isfinite(w).sum(axis=1)
        out[:, c0:c0+1200] = np.where(cnt > 0, v.sum(axis=1) / np.maximum(cnt, 1), np.nan)
    return out
thrS = smooth31(thr)
print("smoothed %.1fs" % (time.time()-t1))

# element checks with correct window (day d -> indices d-16..d+14)
def manual_smooth(a, d):
    return float(np.nanmean(a[(np.arange(d-16, d+15)) % 366]))
for (d, cc) in [(5, 1230), (183, 1230), (366, 3000), (1, 3000), (100, 0)]:
    if not np.isfinite(thr[d-1, cc]):
        continue
    m = manual_smooth(thr[:, cc], d)
    print("smooth chk d=%d c=%d: code %.6f manual %.6f match=%s" % (d, cc, thrS[d-1, cc], m, abs(thrS[d-1, cc]-m) < 1e-12))

# --- hot days + vectorized MHW (different algorithm)
with np.errstate(invalid='ignore'):
    hot = (Y >= thrS[doy_tgt-1])
sea = np.isfinite(Y).all(axis=0)
hot = hot & sea[None, :]
T = hot.shape[0]
pad = np.vstack([np.zeros((1, C), bool), hot, np.zeros((1, C), bool)])
starts = hot & ~pad[:-2]
ends = hot & ~pad[2:]
runlen = np.cumsum(hot, axis=0) - np.flipud(np.cumsum(np.flipud(hot), axis=0)) + 1
runlen = np.where(hot, runlen, 0)
H = hot & (runlen >= 5)
mhw = np.zeros((T, C), bool)
for c in range(C):
    h = H[:, c]
    if not h.any(): continue
    posh = np.flatnonzero(h)
    kp = np.cumsum(h) - 1            # count of H-days strictly before each row
    prevp = np.where(kp > 0, posh[np.clip(kp-1, 0, None)], -1)
    nextp = np.where(kp < len(posh), posh[np.clip(kp, 0, None)], -1)
    fill = (~h) & (prevp >= 0) & (nextp >= 0) & (nextp - prevp <= 3)
    mhw[:, c] = h | fill
print("mhw built %.1fs" % (time.time()-t1))

same = bool((mhw.view(np.uint8) == in_mhw_main).all())
print("FULL MASK MATCH:", same)
if not same:
    diff = (mhw.view(np.uint8) != in_mhw_main)
    print("diff cells:", int(diff.sum()), "at days:", sorted(set(np.flatnonzero(diff).sum() and np.unique(np.argwhere(diff)[:,0]))))

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
