import numpy as np, datetime as dt, warnings

z = np.load('/tmp/region_cube.npz', allow_pickle=True)
dates_str = z['dates']; cube32 = z['cube']
# baseline block: indices 0..4027 (1991-12-27..2003-01-05); target: 4028..4119
BLK = 4028
dates = [dt.datetime.strptime(str(s), '%Y%m%d').date() for s in dates_str]
assert dates[0] == dt.date(1991,12,27) and dates[BLK-1] == dt.date(2003,1,5)
assert dates[BLK] == dt.date(2021,6,1) and dates[-1] == dt.date(2021,8,31)

CUM = [0,31,59,90,120,151,181,212,243,273,304,334]
def doy_map(d):
    if d.month <= 2: return CUM[d.month-1] + d.day
    return CUM[d.month-1] + d.day + 1

doy_arr = np.array([doy_map(d) for d in dates])
print("doy checks: 1991-12-27->", doy_map(dates[0]), " 1992-02-29->", doy_map(dt.date(1992,2,29)),
      " 1993-03-01->", doy_map(dt.date(1993,3,1)), " 1992-12-31->", doy_map(dt.date(1992,12,31)),
      " 2002-12-31->", doy_map(dt.date(2002,12,31)), " 2021-06-01->", doy_map(dates[BLK]),
      " 2021-08-31->", doy_map(dates[-1]))

cube = cube32[:, :, :60].astype(np.float64)   # (4120, 60, 60), drop the extra col
tgt = cube[BLK:]
sea = np.isfinite(tgt).all(axis=0)            # (60,60) bool
print("sea cells:", sea.sum())
sea_flat = sea.reshape(-1)
base = cube[:BLK].reshape(BLK, -1)[:, sea_flat]   # (4028, 3292) float64

# pools: for each baseline anchor j, values at j-5..j+5 (clipped to baseline block) go to pool(doy(j))
anchor_idx = np.arange(5, 5+4018)   # 1992-01-01 .. 2002-12-31
assert dates[5] == dt.date(1992,1,1) and dates[5+4018-1] == dt.date(2002,12,31)
thr_raw = np.full((366, sea_flat.sum()), np.nan)
clim_raw = np.full((366, sea_flat.sum()), np.nan)
warnings.filterwarnings('ignore')
for d in range(1, 367):
    if d == 60: continue
    js = anchor_idx[doy_arr[anchor_idx] == d]
    idx = np.unique(np.concatenate([np.arange(max(0,j-5), min(BLK, j+6)) for j in js]))
    pool = base[idx]                       # (n, C) float64
    thr_raw[d-1] = np.nanquantile(pool, 0.9, axis=0, method='hazen')
    clim_raw[d-1] = np.nanmean(pool, axis=0)
    if d in (1, 59, 61, 365, 366): print(f"d={d}: pool size={len(idx)}, idx {idx[0]}..{idx[-1]}, dates {dates[idx[0]]}..{dates[idx[-1]]}")

# day 60 imputation
thr_raw[59] = (thr_raw[58] + thr_raw[60]) / 2.0
clim_raw[59] = (clim_raw[58] + clim_raw[60]) / 2.0
print("day60 imputed; nan count thr:", np.isnan(thr_raw).sum(), "clim:", np.isnan(clim_raw).sum())

def smooth_wrap(a):  # a: (366, C) -> centred 31-day moving mean, wrap
    pad = np.concatenate([a[-15:], a, a[:15]], axis=0)          # (396, C)
    w = np.lib.stride_tricks.sliding_window_view(pad, 31, axis=0)  # (366, C, 31)
    return w.mean(axis=-1)

thr = smooth_wrap(thr_raw)
clim = smooth_wrap(clim_raw)
print("smoothed shapes:", thr.shape, clim.shape)
print("thr target-period stats: min %.3f max %.3f" % (thr[doy_arr[BLK:]-1].min(), thr[doy_arr[BLK:]-1].max()))
np.savez('/tmp/thr_clim.npz', thr=thr, clim=clim, thr_raw=thr_raw, clim_raw=clim_raw, sea=sea)
print("saved.")
