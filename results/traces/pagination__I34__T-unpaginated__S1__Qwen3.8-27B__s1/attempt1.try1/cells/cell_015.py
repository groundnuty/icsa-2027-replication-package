import numpy as np, datetime

b = np.load("/tmp/mhw/baseline.npy")
idx = [np.asarray(x, dtype=np.int64) for x in np.load("/tmp/mhw/idx_by_doy.npy", allow_pickle=True)]
nsea = b.shape[1]
doys = [d for d in range(1, 367) if d != 60]

thr = np.full((nsea, 366), np.nan)
clim = np.full((nsea, 366), np.nan)
for j, d in enumerate(doys):
    pool = b[idx[j]].T
    thr[:, d-1] = np.nanquantile(pool, 0.9, method="hazen", axis=1)
    clim[:, d-1] = np.nanmean(pool, axis=1)
thr[:, 59] = (thr[:, 58] + thr[:, 60]) / 2.0
clim[:, 59] = (clim[:, 58] + clim[:, 60]) / 2.0

def smooth31(x):
    ext = np.concatenate([x[:, -15:], x, x[:, :15]], axis=1)
    c = np.cumsum(ext, axis=1)
    c = np.concatenate([np.zeros((x.shape[0], 1)), c], axis=1)
    return (c[:, 31:] - c[:, :-31]) / 31.0

thr_s = smooth31(thr)
# cell 0, day 1:
naive = np.concatenate([thr[351:, 0], thr[:16, 0]]).mean()
print("thr_s[0,0] =", thr_s[0, 0], " naive =", naive, " diff =", thr_s[0,0] - naive)
# check ext construction manually
ext = np.concatenate([thr[:, -15:], thr, thr[:, :15]], axis=1)
print("manual mean ext[0..30] cell0:", ext[0, 0:31].mean())
print("thr columns count:", thr.shape)
