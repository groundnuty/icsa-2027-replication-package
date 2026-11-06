import datetime as dt
import numpy as np

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
mask = sea[None] & np.isfinite(tgt)

fflat = np.where(mask, ex, -1e9)
flat_idx = np.argsort(-fflat.ravel())[:25]
print("top 25 excesses:")
for k in flat_idx:
    t, i, j = np.unravel_index(int(k), ex.shape)
    print(" ", tgt_dates[t], f"({i},{j})", f"SST {tgt[t,i,j]:.2f}  thr {thr_t[t,i,j]:.2f}  ex {ex[t,i,j]:+.3f}")

print("\ndate       maxEx  nHot")
for t in range(92):
    e = ex[t][mask[t]]
    print(tgt_dates[t].isoformat(), f"{e.max():+8.3f}", int((e >= 0).sum()))
