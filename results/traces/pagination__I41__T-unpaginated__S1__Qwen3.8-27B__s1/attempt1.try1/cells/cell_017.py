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

# full fresh raw threshold table (all doys)
RAW = np.full((367, n_sea), np.nan)
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=RuntimeWarning)
    for dd in range(1, 367):
        if dd == 60: continue
        RAW[dd, :] = np.nanquantile(M[pool_idx_for(dd), :], 0.9, axis=0, method="hazen")
RAW[60, :] = 0.5*(RAW[59, :] + RAW[61, :])

d2 = np.load('/tmp/mhw_stage2.npz')
saved = d2['thrs']

# For saved values at a few (dd, cell), find nearest fresh (dd, cell)
for dd, jj in [(197,1604), (197, 75), (220, 1000)]:
    sv = saved[dd, jj]
    ddv = np.abs(RAW - sv)
    ddv[60,:] = np.inf
    flat = np.unravel_index(np.argmin(ddv.ravel()), ddv.shape)
    print("saved[%d,%d]=%.4f  nearest fresh: doy=%d cell=%d val=%.4f diff=%.4f" %
          (dd, jj, sv, flat[0], flat[1], RAW[flat], ddv.min()))

# overall: correlation of saved vs fresh across summer doys
mask2 = np.isfinite(saved[152:244]) & np.isfinite(RAW[152:244])
print("corr(saved,fresh) summer:", np.corrcoef(saved[152:244][mask2], RAW[152:244][mask2])[0,1].round(4))
print("mean saved-fresh summer: %.3f" % np.nanmean(saved[152:244]-RAW[152:244]))
np.save('/tmp/RAW_fresh.npy', RAW)
print("RAW saved; master overall max:", np.nanmax(master), " target overall max:", np.nanmax(target))
