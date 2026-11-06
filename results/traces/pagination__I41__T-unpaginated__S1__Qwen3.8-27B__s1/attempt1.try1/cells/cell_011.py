
import numpy as np
from datetime import date, timedelta
d2 = np.load('/tmp/mhw_stage2.npz')
d3 = np.load('/tmp/mhw_stage3.npz')
T, thrs = d2['T'], d2['thrs']
tdoy = d2['tgt_doy']
n_sea = int(d2['n_sea'])

diff = thrs[tdoy] - T          # (92, n_sea); positive = SST below threshold
finite = np.isfinite(diff)
print("min(thr-SST) overall: %.4f K" % diff[finite].min())
print("days where min over cells < 0 K:", int((diff[finite].min(axis=1) < 0).sum()))
# how close overall
print("pct of cell-days with thr-SST < 0.5K:", (diff < 0.5).mean().round(3))
print("pct of cell-days with thr-SST < 1.0K:", (diff < 1.0).mean().round(3))

# warmest cell in target
w = T.max(axis=0)
c = int(np.argmax(w))
print("warmest cell: max SST %.2f K at cell idx %d" % (w[c], c))
print("its smoothed thr over target: min %.2f max %.2f" % (thrs[tdoy, c].min(), thrs[tdoy, c].max()))

# ---- independent single-cell verification of threshold for doy 200 (16 July) ----
dat = np.load('/tmp/sst_data.npz')
master = dat['master']
base_dates = [date(1991,12,27)+timedelta(days=i) for i in range(4028)]
base_all = [date(1992,1,1)+timedelta(days=i) for i in range(4018)]
mdays=[31,29,31,30,31,30,31,31,30,31,30,31]; cum=[0]
for m in mdays: cum.append(cum[-1]+m)
doyf = lambda m,dd: cum[m-1]+dd

cell = sea_i = int(np.unravel_index(c, (60,60))[0])
lat_idx, lon_idx = int(np.unravel_index(c, (60,60)))
def cell_series(dates, offset0):
    vals=[]
    for k,dt in enumerate(dates):
        # find master row index
        row = offset0 + (dt - date(1991,12,27)).days
        vals.append(master[row, lat_idx, lon_idx])
    return np.array(vals)

dd = 200  # 16 July
bs = [b for b in base_all if doy(b.month,b.day)==dd]
pool = sorted(set(t for b in bs for off in range(-5,6)
                  for t in [b+timedelta(days=off)]
                  if date(1991,12,27) <= t <= date(2003,1,5)))
print("doy %d: n baseline dates=%d, pool size=%d, span %s..%s" % (dd, len(bs), len(pool), pool[0], pool[-1]))
vals = np.array([master[(t - date(1991,12,27)).days, lat_idx, lon_idx] for t in pool])
q_haz = np.nanquantile(vals, 0.9, method="hazen")
q_lin = np.nanquantile(vals, 0.9, method="linear")
print("manual thr hazen: %.6f  (pipeline: %.6f)  linear: %.6f" % (q_haz, thrs[dd, c], q_lin))
print("mean: %.6f" % np.nanmean(vals))
