import numpy as np, pandas as pd, warnings, time

sst_base = np.load('/work/sst_base.npy').astype(np.float64)   # (4028,60,60)
sst_tgt  = np.load('/work/sst_tgt.npy').astype(np.float64)    # (92,60,60)
base_dates = pd.read_pickle('/work/base_dates.pkl')
tgt_dates  = pd.read_pickle('/work/tgt_dates.pkl')

CUM = np.array([0,31,59,90,120,151,181,212,243,273,304,334])
def map_doy(ts):
    if ts.month <= 2:
        return int(CUM[ts.month-1] + ts.day)
    return int(CUM[ts.month-1] + ts.day + 1)

base_doy = np.array([map_doy(ts) for ts in base_dates])
tgt_doy  = np.array([map_doy(ts) for ts in tgt_dates])
print("tgt doy range:", tgt_doy[0], "..", tgt_doy[-1])

n = len(base_dates)
start = pd.Timestamp('1991-12-27')
pool = np.zeros((367, n), dtype=bool)
anchor_mask = (base_dates >= '1992-01-01') & (base_dates <= '2002-12-31') & (base_doy != 60)
anchor_idx = np.where(anchor_mask)[0]
print("n anchors:", anchor_idx.size)   # expect 11 years * 365 = 4015
for k in anchor_idx:
    d = base_doy[k]
    pool[d, max(0,k-5):min(n,k+6)] = True

sizes = pool[1:].sum(axis=1)
sizes[60] = 0
print("pool size per doy: min", sizes[1:].min(), "max", sizes[1:].max(), "(expect 121)")
used = pool.any(axis=0)
print("baseline-ext dates used in >=1 pool:", int(used.sum()), "of", n)
print("used first/last:", base_dates[used][0].date(), base_dates[used][-1].date())
print("all used dates contiguous:", bool(used.all()))

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
print("clim/thr computed in %.1fs" % (time.time()-t0))

def smooth31(pre):
    out = np.zeros_like(pre)
    for off in range(-15, 16):
        out += np.roll(pre, off, axis=0)
    return out / 31.0
thr_s, clim_s = smooth31(thr), smooth31(clim)

sea = np.isfinite(sst_tgt).all(axis=0)
print("sea cells (finite all 92 target days):", int(sea.sum()), "of 3600")
# is the NaN mask constant across target days?
nfin = np.isfinite(sst_tgt).sum(axis=0)
print("cells finite on some-but-not-all target days:", int(((nfin>0)&(nfin<92)).sum()))
# baseline finiteness on sea cells
print("sea-cell finite fraction in baseline pool days:", float(np.isfinite(sst_base[:, sea]).mean()))

np.savez('/work/clim_thr.npz', thr=thr, clim=clim, thr_s=thr_s, clim_s=clim_s,
         sea=sea, tgt_doy=tgt_doy)
print("sample clim (sea mean) by doy 152,182,244:",
      float(np.nanmean(clim_s[153][sea])), float(np.nanmean(clim_s[182][sea])), float(np.nanmean(clim_s[244][sea])))
print("sample thr  (sea mean) by doy 153,182,244:",
      float(np.nanmean(thr_s[153][sea])), float(np.nanmean(thr_s[182][sea])), float(np.nanmean(thr_s[244][sea])))
