import numpy as np, datetime as dt
S_tgt = np.load('/work/S_tgt.npy').reshape(92, -1)
thr_s = np.load('/work/thr_s.npy')
sea_cells = np.load('/work/sea_cells.npy')
tgt_doy = np.load('/work/tgt_doy.npy')
tgt_dates = [dt.date.fromisoformat(str(d)) for d in np.load('/work/coords.npz')['target_dates'].astype('datetime64[D]').astype(object)]
S_base = np.load('/work/S_base.npy')

margin = S_tgt - thr_s[tgt_doy]
m = margin[:, sea_cells]
for i in range(0, 92, 5):
    row = m[i]
    print(tgt_dates[i].isoformat(), f"doy={tgt_doy[i]:3d}  SST_med={np.nanmedian(S_tgt[i, sea_cells]):7.3f}  thr_med={np.nanmedian(thr_s[tgt_doy[i], sea_cells]):7.3f}  max_margin={row.max():7.3f}  n_hot={(row>=0).sum():4d}")

# raw (unsmoothed) threshold check for a mid-summer doy: recompute one pool for one cell manually
c = sea_cells[1800]
print("\ncheck cell", c, "lat/lon:", round(float(np.load('/work/coords.npz')['lat'][c//60]),3), round(float(np.load('/work/coords.npz')['lon'][c%60]),3))
# pool for doy 197 (Jul 15, 2004 -> doy? 153+30+31-? compute)
print("doy of 2004-07-15:", )
def doy(d):
    cum=[0]
    for L in [31,29,31,30,31,30,31,31,30,31,30,31]: cum.append(cum[-1]+L)
    return cum[d.month-1]+d.day
print(doy(dt.date(2004,7,15)))
# pool dates for d=196: Jul 14 of each year 1992..2002, window ±5
base_dates = [dt.date.fromisoformat(str(d)) for d in np.load('/work/coords.npz')['baseline_dates'].astype('datetime64[D]').astype(object)]
d2 = doy(dt.date(2004,7,15))
vals = []
for y in range(1992, 2003):
    b = dt.date(y, 7, 14) if d2==196 else None
pool = []
for y in range(1992, 2003):
    b = dt.date(y, 7, 14)
    for k in range(-5, 6):
        pool.append(b + dt.timedelta(days=k))
idx = {d:i for i,d in enumerate(base_dates)}
X = S_base[[idx[p] for p in pool]].reshape(-1, 60, 60)[:, c//60, c%60]
X = X[np.isfinite(X)]
q = np.quantile(X, 0.9, method='hazen')
print(f"manual pool n={len(X)}, thr={q:.4f}, thr_s[196-1, c]={thr_s[195, c]:.4f}")
# 2004 Jul 15 SST at that cell
i15 = tgt_dates.index(dt.date(2004,7,15))
print("2004-07-15 SST:", S_tgt[i15, c], "margin:", S_tgt[i15, c]-thr_s[195, c])
