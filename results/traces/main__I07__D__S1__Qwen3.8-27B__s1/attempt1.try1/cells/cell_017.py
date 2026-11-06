import numpy as np
S_base = np.load('/work/S_base.npy')  # (4028, 60, 60)
M = np.load('/work/M.npy')            # (366, 4028)
N = S_base.shape[0]
NC = S_base.shape[1] * S_base.shape[2]
flat = S_base.reshape(N, NC)

thr = np.full((366, NC), np.nan)
clim = np.full((366, NC), np.nan)
for d in range(366):
    if d == 59:  # day 60: no pool
        continue
    idx = np.where(M[d])[0]
    sub = flat[idx]  # (121, NC)
    thr[d] = np.nanpercentile(sub, 90, method='hazen', axis=0)
    clim[d] = np.nanmean(sub, axis=0)

neq60 = np.arange(366) != 59
print("NaNs in thr (d!=60):", np.isnan(thr[neq60]).sum())
print("NaNs in clim (d!=60):", np.isnan(clim[neq60]).sum())

thr[59] = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])
print("NaNs after fill:", np.isnan(thr).sum(), np.isnan(clim).sum())

def smooth31(a):
    out = np.empty_like(a)
    idx = (np.arange(366)[:, None] - 15 + np.arange(31)[None, :]) % 366
    for s in range(0, 366, 36):
        e = min(s+36, 366)
        out[s:e] = np.take(a, idx[s:e], axis=0).mean(axis=1)
    return out

a_test = np.arange(366, dtype=float)
sm = smooth31(a_test)
direct = np.mean([ (0 - 15 + j) % 366 for j in range(31) ])
print("smooth check day1:", sm[0], "direct:", direct)
direct2 = np.mean([ (17 - 15 + j) % 366 for j in range(31) ])
print("smooth check day18:", sm[17], "direct:", direct2)
direct3 = np.mean([ (365 - 15 + j) % 366 for j in range(31) ])
print("smooth check day366:", sm[365], "direct:", direct3)

thr_s = smooth31(thr)
clim_s = smooth31(clim)
print("thr_s range:", thr_s.min(), thr_s.max())
print("clim_s range:", clim_s.min(), clim_s.max())
np.save('/work/thr_s.npy', thr_s)
np.save('/work/clim_s.npy', clim_s)
