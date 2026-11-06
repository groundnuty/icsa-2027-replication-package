import numpy as np, pandas as pd, warnings, time

sst_base = np.load('/work/sst_base.npy').astype(np.float64)
sst_tgt  = np.load('/work/sst_tgt.npy').astype(np.float64)
base_dates = pd.read_pickle('/work/base_dates.pkl')
tgt_dates  = pd.read_pickle('/work/tgt_dates.pkl')

CUM = np.array([0,31,59,90,120,151,181,212,243,273,304,334])
def map_doy(ts):
    if ts.month <= 2:
        return int(CUM[ts.month-1] + ts.day)
    return int(CUM[ts.month-1] + ts.day + 1)

base_doy = np.array([map_doy(ts) for ts in base_dates])
tgt_doy  = np.array([map_doy(ts) for ts in tgt_dates])

n = len(base_dates)
pool = np.zeros((367, n), dtype=bool)
anchor_mask = (base_dates >= '1992-01-01') & (base_dates <= '2002-12-31') & (base_doy != 60)
for k in np.where(anchor_mask)[0]:
    d = base_doy[k]
    pool[d, max(0,k-5):min(n,k+6)] = True
sizes = pool[1:].sum(axis=1); sizes[60] = 0
print("pool size per doy (excl 60): min", sizes.min(), "max", sizes.max())
used = pool.any(axis=0)
print("all 4028 baseline-ext dates used:", bool(used.all()),
      "| first used:", base_dates[used].min().date(), "last used:", base_dates[used].max().date())

t0 = time.time()
thr  = np.full((367, 60, 60), np.nan)
clim = np.full((367, 60, 60), np.nan)
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for d in range(1, 367):
        if d == 60: continue
        vals = sst_base[pool[d]]
        thr[d]  = np.nanpercentile(vals, 90, axis=0, method='hazen')
        clim[d] = np.nanmean(vals, axis=0)
thr[60]  = (thr[59] + thr[61]) / 2.0
clim[60] = (clim[59] + clim[61]) / 2.0
print("clim/thr raw computed in %.1fs" % (time.time()-t0))

def smooth31(pre):
    out = np.zeros_like(pre)
    for off in range(-15, 16):
        out += np.roll(pre, off, axis=0)
    return out / 31.0
thr_s, clim_s = smooth31(thr), smooth31(clim)

sea = np.isfinite(sst_tgt).all(axis=0)
nfin = np.isfinite(sst_tgt).sum(axis=0)
print("sea cells:", int(sea.sum()), "| finite-on-some-but-not-all-target:", int(((nfin>0)&(nfin<92)).sum()))
print("NaN mask identical across all 92 target days:",
      bool(np.array_equal(np.isnan(sst_tgt[0]), np.isnan(sst_tgt[-1]))))
print("sea-cell baseline finite fraction:", float(np.isfinite(sst_base[:, sea]).mean()))
# per-sea-cell: any NaN in the pools?
any_nan = np.zeros(367, bool)
for d in range(1,367):
    if d==60: continue
    any_nan[d] = np.isnan(sst_base[pool[d]]).any()
print("any NaN in pools:", bool(any_nan.any()))

np.savez('/work/clim_thr.npz', thr=thr, clim=clim, thr_s=thr_s, clim_s=clim_s,
         sea=sea, tgt_doy=tgt_doy)
print("saved clim_thr.npz")
