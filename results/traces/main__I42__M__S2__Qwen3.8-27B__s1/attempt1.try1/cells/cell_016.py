import numpy as np, pickle
from collections import defaultdict

base = np.load('/tmp/base.npy')
time_all = np.load('/tmp/time_all.npy')
base_dates = time_all[3647:7675]
target = np.load('/tmp/target.npy').reshape(92, -1)
target_dates = time_all[11109:11201]
thr_s = np.load('/tmp/thr_s.npy')
clim_s = np.load('/tmp/clim_s.npy')
mask = np.load('/tmp/mask.npy').reshape(92, -1)

LEAP_CUM = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
def doy366(dates):
    dates = np.asarray(dates).astype('datetime64[D]')
    m = (dates.astype('datetime64[M]') - dates.astype('datetime64[Y]')).astype(int) + 1
    d = (dates - dates.astype('datetime64[M]')).astype(int) + 1
    return LEAP_CUM[m - 1] + d

bmin = np.datetime64('1992-01-01'); bmax = np.datetime64('2002-12-31')
pools = defaultdict(list)
for k in range(-5, 6):
    b = base_dates + np.timedelta64(k, 'D')
    msk = (b >= bmin) & (b <= bmax)
    for i, dd in zip(np.where(msk)[0].tolist(), doy366(b[msk]).tolist()):
        pools[dd].append(i)

# (a) manual hazen check: cell 1798, doy 153
c = 1798
d = 153
col = base[pools[d], 29, 31]   # cell (29,31) == 29*60+31 = 1791? no: 1798 = 29*60+58
# 1798 // 60 = 29, 1798 % 60 = 58
col = base[pools[d], 29, 58]
x = col[~np.isnan(col)]
x = np.sort(x)
n = len(x)
h = (n + 0.5) * 0.9      # 1-based position (hazen inverse)
i0 = int(np.floor(h))
frac = h - i0
if i0 >= n:
    manual = x[-1]
else:
    manual = x[i0 - 1] + frac * (x[i0] - x[i0 - 1])
np_val = np.nanquantile(col, 0.9, method='hazen')
print(f"cell {c} doy {d}: n={n} manual={manual!r} numpy={np_val!r} equal={np.isclose(manual, np_val)}")

# (b) check around the event: find cells in mask on Aug 17 (day idx: Aug 17 = 2012-08-17)
d_idx = {str(td)[:10]: i for i, td in enumerate(target_dates)}
i_aug15, i_aug19 = d_idx['2012-08-15'], d_idx['2012-08-19']
print("aug15 idx", i_aug15, "aug19 idx", i_aug19)
ev_cells = np.where(mask[i_aug15, :])[0]
print("cells active on Aug 15:", len(ev_cells))
c0 = int(ev_cells[0])
print("cell", c0, "lat/lon:", np.load('/tmp/lat.npy')[c0//60], np.load('/tmp/lon.npy')[c0%60])
doy_t = np.arange(153, 245)
for i in range(i_aug15 - 6, i_aug19 + 7):
    dd = doy_t[i]
    print(f"{target_dates[i]} doy {dd}  SST={target[i, c0]:.3f}  thr={thr_s[dd-1, c0]:.3f}  hot={target[i, c0] >= thr_s[dd-1, c0]}  inMHW={mask[i, c0]}")

# (c) mask boundary check for that cell
row = mask[:, c0]
print("mask row for cell", c0, ":", np.where(row)[0])
# check no other day in region has mask
print("total mask cells-days:", int(mask.sum()), " event cells sum:", int(mask.sum(axis=0).sum()))
# per-cell event day ranges
evcells_all = np.where(mask.any(axis=0))[0]
ranges = {}
for cc in evcells_all:
    rr = np.where(mask[:, cc])[0]
    ranges[cc] = (rr.min(), rr.max())
uniq = sorted(set(ranges.values()))
print("unique day-ranges among cells:", uniq)
