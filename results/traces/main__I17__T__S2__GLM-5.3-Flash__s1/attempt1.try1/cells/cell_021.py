import numpy as np, datetime as dt

me = '/work/me/'
thr_s = np.load(me+'thr_s.npy'); clim_s = np.load(me+'clim_s.npy')
b64 = np.load(me+'base.npy').astype(np.float64)
epoch = dt.date(1991,12,27)
seeds = {d: [] for d in range(1,367)}
cur = dt.date(1992,1,1)
while cur <= dt.date(2002,12,31):
    seeds[dt.date(2000,cur.month,cur.day).timetuple().tm_yday].append((cur-epoch).days)
    cur += dt.timedelta(days=1)
Nb = b64.shape[0]
y, x = 10, 10
raw = np.empty(366)
nans = []
for d in range(1,367):
    if d == 60: continue
    m = np.zeros(Nb, bool)
    for s in seeds[d]: m[max(0,s-5):min(Nb,s+6)] = True
    vals = b64[m][:, y, x]
    raw[d-1] = np.nanmean(vals)
    if not np.isfinite(raw[d-1]):
        nans.append((d, int(np.isfinite(vals).sum()), len(vals)))
print("all-NaN pools at cell (10,10):", nans)
raw[59] = 0.5*(raw[58] + raw[60])
# proper d366 check: days 351..366 + 1..15
exp366 = np.concatenate([raw[350:366], raw[0:15]]).mean()
print("d366 smooth %.6f vs %.6f" % (clim_s[365,y,x], exp366))
# and d1: days 352..366 + 1..16
exp1 = np.concatenate([raw[351:366], raw[0:16]]).mean()
print("d1   smooth %.6f vs %.6f" % (clim_s[0,y,x], exp1))

# NaN scan over full region in smoothed arrays
print("NaNs in thr_s:", int(np.isnan(thr_s).sum()), "of", thr_s.size,
      "| NaNs in clim_s:", int(np.isnan(clim_s).sum()))
# which cells/doys are NaN?
nn = np.argwhere(np.isnan(thr_s))
if len(nn):
    doys, cells = np.unique(nn[:,0]), np.unique(nn[:,1]*60+nn[:,2])
    print("nan doys:", doys.min()+1, "..", doys.max()+1, "count:", len(doys))
    print("nan cells:", len(cells))
    ys, xs = nn[0,1], nn[0,2]
    print("example nan cell:", ys, xs)
