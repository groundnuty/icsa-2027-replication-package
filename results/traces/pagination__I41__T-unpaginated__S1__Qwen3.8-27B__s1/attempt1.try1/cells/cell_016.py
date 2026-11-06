import numpy as np, warnings
from datetime import date, timedelta

dat = np.load('/tmp/sst_data.npz')
master = dat['master']; target = dat['target']
sea_mask = np.isfinite(target).all(axis=0)
sea_cells = np.argwhere(sea_mask)
n_sea = len(sea_cells)
M = np.empty((4028, n_sea), np.float64)
for j, (i, k) in enumerate(sea_cells):
    M[:, j] = master[:, i, k]

base_dates = [date(1991,12,27)+timedelta(days=i) for i in range(4028)]
base_all   = [date(1992,1,1)+timedelta(days=i) for i in range(4018)]
mord = np.array([x.toordinal() for x in base_dates])
bords = np.array([x.toordinal() for x in base_all])
mdays=[31,29,31,30,31,30,31,31,30,31,30,31]; cum=[0]
for m in mdays: cum.append(cum[-1]+m)
doyf = lambda m,dd: cum[m-1]+dd
bdoy = np.array([doyf(x.month, x.day) for x in base_all])

def pool_idx_for(dd):
    b = bords[bdoy == dd]
    mask = np.zeros(4028, dtype=bool)
    for bo in b:
        mask |= (mord >= bo-5) & (mord <= bo+5)
    return np.where(mask)[0]

d2 = np.load('/tmp/mhw_stage2.npz')
saved = d2['thrs']

for dd in (197, 200, 190):
    idx = pool_idx_for(dd)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        raw = np.nanquantile(M[idx, :], 0.9, axis=0, method="hazen")
    print("doy", dd, "raw thr: min %.2f max %.2f" % (np.nanmin(raw), np.nanmax(raw)))
    # does saved column 1604's value appear anywhere in fresh raw?
    sv = saved[dd, 1604]
    close = np.where(np.abs(raw - sv) < 0.05)[0]
    print("  saved[dd,1604]=%.3f matches fresh raw at cells:" % sv, close[:10],
          "-> region idx", [tuple(sea_cells[c]) for c in close[:5]])
    # and what does fresh raw say for cell 1604?
    print("  fresh raw[1604] = %.3f" % raw[1604])
