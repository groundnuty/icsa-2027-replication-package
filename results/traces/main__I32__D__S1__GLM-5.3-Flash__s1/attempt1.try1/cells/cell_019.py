import numpy as np, json
from datetime import date, timedelta

T = np.load('/work/T.npy')
thr = np.load('/work/thr_raw.npy'); clm = np.load('/work/clm_raw.npy')
sea = np.isfinite(T).all(axis=0)
print("thr finite on all sea cells:", np.isfinite(thr[:, sea]).all())
print("clm finite on all sea cells:", np.isfinite(clm[:, sea]).all())
print("thr NaN cells (=land?):", int(np.isnan(thr[0]).sum()), " land count:", int((~sea).sum()))
print("NaN pattern identical to land:", np.array_equal(np.isnan(thr[0]), ~sea))
print("clm NaN pattern identical to land:", np.array_equal(np.isnan(clm[0]), ~sea))

# sanity: thr >= clm? (roughly, for 90th pct vs mean) - check on sea cells
sc = np.argwhere(sea)
frac = np.mean([np.mean(thr[:,r,c] >= clm[:,r,c]) for r,c in sc[:200]])
print("fraction of doy-cell combos with thr>=clm (200 cells):", frac)

# ---- smoothing: unweighted centred 31-day moving mean, wrap over 366 days ----
def smooth(x):
    # x: (366, ...) with NaN only on land; moving mean over wrapped 31-day window
    pad = np.concatenate([x[-15:], x, x[:15]], axis=0)   # (396, ...)
    kern = np.ones(31)
    num = fftconvolve(pad, kern[:, None, None] if x.ndim == 3 else kern, mode='valid', axes=(0,)) if False else None
    return None
# do it simply with cumsum-based sliding window (vectorised, exact, float64)
def smooth_wrap(x):
    # x: (366, 60, 60)
    pad = np.concatenate([x[-15:], x, x[:15]], axis=0)   # (396,60,60)
    csum = np.concatenate([np.zeros((1,)+x.shape[1:]), np.cumsum(pad, axis=0)], axis=0)
    out = (csum[31:] - csum[:-31]) / 31.0
    return out  # (366,60,60)

thr_s = smooth_wrap(thr)
clm_s = smooth_wrap(clm)
print("smoothed shapes:", thr_s.shape, clm_s.shape)
print("smoothed finite on sea:", np.isfinite(thr_s[:, sea]).all(), np.isfinite(clm_s[:, sea]).all())
# verify against brute force on a couple of entries
r,c = sc[0]
def brute(arr, d, r, c):
    idxs = [((d-1+k) % 366) for k in range(-15,16)]
    return np.mean([arr[i, r, c] for i in idxs])
for dtest in [1, 60, 153, 244, 366]:
    print(dtest, brute(thr, dtest, r, c), thr_s[dtest-1, r, c],
          "match:", abs(brute(thr, dtest, r, c) - thr_s[dtest-1, r, c]) < 1e-12)
np.save('/work/thr_s.npy', thr_s); np.save('/work/clm_s.npy', clm_s)
print("saved smoothed")
