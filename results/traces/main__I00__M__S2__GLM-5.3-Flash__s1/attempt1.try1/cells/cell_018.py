script = r'''
import numpy as np

thresh_raw = np.load("/tmp/mhw_work/thresh_raw.npy")   # (366, 60, 60)
clim_raw = np.load("/tmp/mhw_work/clim_raw.npy")

def smooth_wrap(a):
    # a: (366, ...) unweighted centred 31-day moving mean, wrapping modulo 366
    n = a.shape[0]
    ap = np.concatenate([a[-15:], a, a[:15]], axis=0)   # length 366+30
    kernel = np.ones(31) / 31.0
    if a.ndim == 1:
        return np.convolve(ap, kernel, mode="valid")
    out = np.empty_like(a)
    for k in range(a.shape[1]):
        for l in range(a.shape[2]):
            out[:, k, l] = np.convolve(ap[:, k, l], kernel, mode="valid")
    return out

# do it vectorised over space instead of loops
def smooth_wrap2(a):
    n = a.shape[0]
    ap = np.concatenate([a[-15:], a, a[:15]], axis=0)
    c = np.cumsum(ap, axis=0)
    # sum over window of 31 ending at index i+30: c[i+30] - c[i-1]
    hi = c[30:]
    lo = np.concatenate([np.zeros((1,)+a.shape[1:]), c[:-31]], axis=0)
    return (hi - lo) / 31.0

thresh = smooth_wrap2(thresh_raw)
clim = smooth_wrap2(clim_raw)

# verify against the loop version on a few cells
sm_loop_thresh = smooth_wrap(thresh_raw[:, 28, 59])
sm_loop_clim = smooth_wrap(clim_raw[:, 28, 59])
print("thresh match loop vs vector:", np.allclose(thresh[:, 28, 59], sm_loop_thresh))
print("clim match loop vs vector:", np.allclose(clim[:, 28, 59], sm_loop_clim))

# sanity: smoothing preserves overall level
print("raw thresh mean over sea/doy:", float(np.nanmean(thresh_raw)), " smoothed:", float(np.nanmean(thresh)))
print("raw clim mean over sea/doy:", float(np.nanmean(clim_raw)), " smoothed:", float(np.nanmean(clim)))
# wrap check: day 1 uses days 352..366 and 1..16
i, j = 28, 59
manual = np.mean([thresh_raw[(d-1) % 366, i, j] for d in list(range(352, 367)) + list(range(1, 17))])
print("day 1 smoothed manual:", manual, " computed:", thresh[0, i, j])
np.save("/tmp/mhw_work/thresh.npy", thresh)
np.save("/tmp/mhw_work/clim.npy", clim)
print("saved smoothed arrays")
'''
open("/tmp/mhw_work/smooth.py", "w").write(script)
exec(open("/tmp/mhw_work/smooth.py").read())
