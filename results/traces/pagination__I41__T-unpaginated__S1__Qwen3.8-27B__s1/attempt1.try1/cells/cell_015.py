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

# raw threshold for cell j=1604 across doys 150..250
j = 1604
idx197 = pool_idx_for(197)
col = M[:, j]
print("M column j=1604: max=%.2f" % col[np.isfinite(col)].max())
blk = M[idx197, j]
print("pool197 blk: nfin=%d min=%.2f max=%.2f hazen90=%.4f" % (
    np.isfinite(blk).sum(), np.nanmin(blk), np.nanmax(blk), np.nanquantile(blk,0.9,method='hazen')))

d2 = np.load('/tmp/mhw_stage2.npz')
# compare raw? we only saved smoothed thrs. Compare smoothed for doys 150..250, cell j
def smooth366(a):
    s = np.zeros_like(a)
    for k in range(-15, 16):
        s += np.roll(a, -k, axis=0)
    return s / 31.0

thr = np.full((367, n_sea), np.nan)
clim = np.full((367, n_sea), np.nan)
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=RuntimeWarning)
    for dd in range(1, 367):
        if dd == 60: continue
        blk2 = M[pool_idx_for(dd), :]
        thr[dd, :] = np.nanquantile(blk2, 0.9, axis=0, method="hazen")
        clim[dd, :] = np.nanmean(blk2, axis=0)
thr[60, :] = 0.5*(thr[59, :] + thr[61, :])
clim[60, :] = 0.5*(clim[59, :] + clim[61, :])
thrs_fixed = smooth366(thr[0:366])   # indices 0..365 (doy 0..365); doy d at index d
print("fresh thrs[197,1604] =", thrs_fixed[197, j])
print("saved thrs[197,1604] =", d2['thrs'][197, j])
# compare whole arrays
saved = d2['thrs']
print("max abs diff fresh vs saved over summer doys, all cells:", np.nanmax(np.abs(thrs_fixed[150:250] - saved[150:250])))
# where do they differ most?
diffarr = np.nanmax(np.abs(thrs_fixed[150:250] - saved[150:250]), axis=0)
print("cells with diff>0.1 K:", int((diffarr > 0.1).sum()), "of", n_sea)
print("argmax diff cell:", int(np.argmax(diffarr)), "value:", diffarr.max())
