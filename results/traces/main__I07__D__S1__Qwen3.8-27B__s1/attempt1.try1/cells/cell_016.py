import numpy as np
S_base = np.load('/work/S_base.npy')  # (4028, 60, 60)
M = np.load('/work/M.npy')            # (366, 4028)

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

print("NaNs in thr (d!=60):", np.isnan(thr[neq60:=np.arange(366)!=59]).sum())
print("NaNs in clim (d!=60):", np.isnan(clim[neq60]).sum())

# day 60 = mean of days 59 and 61
thr[59] = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])
print("NaNs after fill:", np.isnan(thr).sum(), np.isnan(clim).sum())

# 31-day centred wrapped moving mean
def smooth31(a):
    # a: (366, ...) -> average over days d-15..d+15 mod 366
    out = np.empty_like(a)
    idx = (np.arange(366)[:, None] - 15 + np.arange(31)[None, :]) % 366  # (366,31)
    for s in range(0, 366, 36):
        e = min(s+36, 366)
        out[s:e] = np.take(a, idx[s:e], axis=0).mean(axis=1)
    return out

# verify against direct loop for a couple of days
a_test = np.arange(366, dtype=float)
sm = smooth31(a_test)
d = 1  # 0-based 0
expect = np.mean([( (0-15+366)%366 + k) for k in range(31) ] if False else [((0+k)%366) for k in range(31)])
# direct: days d-15..d+15 for d=1 (1-based) => 1-based -14..16 => 0-based (-15..15) mod 366
direct = np.mean([ (0 - 15 + j) % 366 for j in range(31) ])
print("smooth check day1:", sm[0], "direct:", direct)
direct2 = np.mean([ (17 - 15 + j) % 366 for j in range(31) ])
print("smooth check day18:", sm[17], "direct:", direct2)

thr_s = smooth31(thr)
clim_s = smooth31(clim)
print("thr_s range:", thr_s.min(), thr_s.max())
print("clim_s range:", clim_s.min(), clim_s.max())
np.save('/work/thr_s.npy', thr_s)
np.save('/work/clim_s.npy', clim_s)
