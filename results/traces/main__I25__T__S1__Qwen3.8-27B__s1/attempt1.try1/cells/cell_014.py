
import numpy as np, datetime as dt, time, warnings
np.printoptions(precision=4, suppress=True)
warnings.filterwarnings('ignore', category=RuntimeWarning)
sst_base = np.load('/tmp/sst_base.npy')
bord = np.load('/tmp/bdates.npy'); tor = np.load('/tmp/tdates.npy')

def doy_of(ordinal):
    d = dt.date.fromordinal(int(ordinal))
    cum = [31,29,31,30,31,30,31,31,30,31,30,31]
    return sum(cum[:d.month-1]) + d.day

t0=time.time()
b_doy = np.array([doy_of(o) for o in bord])
t_doy = np.array([doy_of(o) for o in tor])

b0 = dt.date(1992,1,1).toordinal(); b1 = dt.date(2002,12,31).toordinal()
rows_of_doy = {d: [] for d in range(1,367)}
for i, o in enumerate(bord):
    lo = max(int(o)-5, b0); hi = min(int(o)+5, b1)
    for b in range(lo, hi+1):
        rows_of_doy[doy_of(b)].append(i)
assert all(len(rows_of_doy[d])==121 for d in range(1,367) if d!=60)

NC = 3600
thr  = np.full((367, NC), np.nan)
clim = np.full((367, NC), np.nan)
for d in range(1,367):
    if d == 60: continue
    pool = sst_base[rows_of_doy[d]]
    thr[d]  = np.nanquantile(pool, 0.90, axis=0, method='hazen')
    clim[d] = np.nanmean(pool, axis=0)
print("pools %.1f s" % (time.time()-t0))

thr[60]  = 0.5*(thr[59]+thr[61])
clim[60] = 0.5*(clim[59]+clim[61])

def smooth366(a366):
    y = np.r_[a366[-15:], a366, a366[:15]]
    return y.reshape(366,31).mean(axis=1)

x = thr[1:]; xc = clim[1:]
thr_s  = smooth366(x)
clim_s = smooth366(xc)
ok = True
for d in [1, 20, 60, 153, 244, 352, 366]:
    i = d-1
    idxs = np.array([(i+k) % 366 for k in range(-15,16)])
    ref = x[idxs].mean(axis=0)
    if not np.allclose(ref, thr_s[i]): ok=False; print("MISMATCH", d)
print("smoothing check:", "ok" if ok else "FAIL")
print("thr_s range:", np.nanmin(thr_s), np.nanmax(thr_s), "NaNs:", int(np.isnan(thr_s).sum()))
print("clim_s range:", np.nanmin(clim_s), np.nanmax(clim_s), "NaNs:", int(np.isnan(clim_s).sum()))
print("thr[153] sample:", thr_s[152][1500:1505])
np.save('/tmp/thr_s.npy', thr_s); np.save('/tmp/clim_s.npy', clim_s)
np.save('/tmp/t_doy.npy', t_doy)
print("saved, total %.1f s" % (time.time()-t0))
