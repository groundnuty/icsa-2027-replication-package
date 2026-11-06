import numpy as np, time

thr = np.load('/work/thr_unsmoothed.npy')   # (366, C)
clim = np.load('/work/clim_unsmoothed.npy')
print(thr.shape, clim.shape)

# wraparound centred 31-day moving mean along axis 0
def moving_mean_wrap(a, win=31):
    half = win // 2  # 15
    out = np.empty_like(a)
    rolled_sums = None
    # efficient: cumulative approach with wrap; win=31 odd
    n = a.shape[0]
    x = np.concatenate([a[n-half:, :], a, a[:half, :]], axis=0)  # length n+30
    cs = np.vstack([np.zeros((1, a.shape[1])), np.cumsum(x, axis=0)])  # (n+31, C)
    out = (cs[win:] - cs[:n]) / win
    return out

# quick self-test
test = np.arange(366, dtype=float).reshape(366, 1)
mm = moving_mean_wrap(test)
print("mm[0] expect mean of 351..365,0..15 =", test[351:366].mean() + 0)  # compute directly
direct = np.array([test[(np.arange(366)[d] + np.arange(-15,16)) % 366].mean() for d in range(366)])
print("wrap mm matches direct:", np.allclose(mm.ravel(), direct))
# also test local (no wrap) element: mm[100] should equal mean of 85..115
print("mm[100] ok:", np.isclose(mm[100,0], np.arange(85,116).mean()))

t0 = time.time()
thr_s = moving_mean_wrap(thr)
clim_s = moving_mean_wrap(clim)
print(f"smoothing {time.time()-t0:.2f}s")
print("finite:", np.isfinite(thr_s).all(), np.isfinite(clim_s).all())
print("thr_s range:", thr_s.min(), thr_s.max(), "| clim_s range:", clim_s.min(), clim_s.max())
np.save('/work/thr_smoothed.npy', thr_s)
np.save('/work/clim_smoothed.npy', clim_s)
