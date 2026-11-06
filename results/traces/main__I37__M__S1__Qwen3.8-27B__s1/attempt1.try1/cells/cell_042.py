import datetime as dt
import numpy as np

ext = np.load('/work/chk/ext.npy').astype(np.float64)
tgt = np.load('/work/chk/tgt.npy').astype(np.float64)
sea = np.load('/work/chk/sea.npy')
thr = np.load('/work/chk/thr.npy')

def daterange(a, b):
    d, out = a, []
    while d <= b:
        out.append(d); d += dt.timedelta(days=1)
    return out
tgt_dates = daterange(dt.date(2012,6,1), dt.date(2012,8,31))
doy_tgt = np.array([dt.date(2000, d.month, d.day).timetuple().tm_yday for d in tgt_dates])
thr_t = thr[doy_tgt - 1]
ex = tgt - thr_t
valid = sea[None] & np.isfinite(tgt)
mask = valid

# top 25 excesses
flat = np.where(mask, ex, np.nan)
idx = np.dstack(np.unravel_index(np.nanargmax(flat * 1 - np.abs(flat) * 0, axis=None) , flat.shape))  # placeholder
order = np.argsort(-np.nan_to_num(flat, nan=-1e9))[:25]
print("top 25 excesses (date, lat_idx, lon_idx, SST, thr, excess):")
for k in order:
    t, i, j = np.unravel_index(k, ex.shape)
    print(" ", tgt_dates[t], i, j, f"{tgt[t,i,j]:.2f} {thr_t[t,i,j]:.2f} {ex[t,i,j]:+.3f}")

# per-day max excess and hot count
print("\ndate      maxEx  nHot")
for t in range(92):
    e = ex[t][mask[t]]
    print(tgt_dates[t].isoformat(), f"{e.max():+7.3f}", int((e >= 0).sum()))
