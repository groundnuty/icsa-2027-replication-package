import numpy as np, warnings
from datetime import date, timedelta
import xarray as xr

dat = np.load('/tmp/sst_data.npz')
master = dat['master']; target = dat['target']
chk = xr.open_dataset('output/mhw_mask.nc'); mask_out = chk['mhw'].values; t_out = chk['time'].values; chk.close()

def daterange(a,b):
    o=[]
    while a<=b: o.append(a); a+=timedelta(days=1)
    return o
base_dates = daterange(date(1991,12,27), date(2003,1,5))
tgt_dates  = daterange(date(2021,6,1), date(2021,8,31))
base_all   = daterange(date(1992,1,1), date(2002,12,31))
mdays=[31,29,31,30,31,30,31,31,30,31,30,31]; cum=[0]
for m in mdays: cum.append(cum[-1]+m)
doyf = lambda m,dd: cum[m-1]+dd

sea_mask = np.isfinite(target).all(axis=0)
sea_cells = np.argwhere(sea_mask)
n_sea = len(sea_cells)
M = np.empty((4028, n_sea), np.float64); T = np.empty((92, n_sea), np.float64)
for j, (i, k) in enumerate(sea_cells):
    M[:, j] = master[:, i, k]; T[:, j] = target[:, i, k]
mord  = np.array([x.toordinal() for x in base_dates])
bords = np.array([x.toordinal() for x in base_all])
bdoy  = np.array([doyf(x.month, x.day) for x in base_all])
thr = np.full((366, n_sea), np.nan)
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=RuntimeWarning)
    for dd in range(1, 367):
        if dd == 60: continue
        b = bords[bdoy == dd]; mask = np.zeros(4028, dtype=bool)
        for bo in b: mask |= (mord >= bo-5) & (mord <= bo+5)
        thr[dd-1, :] = np.nanquantile(M[np.where(mask)[0], :], 0.9, axis=0, method="hazen")
thr[59, :] = 0.5*(thr[58, :] + thr[60, :])
def smooth366(a):
    s = np.zeros_like(a)
    for k in range(-15, 16): s += np.roll(a, -k, axis=0)
    return s/31.0
thrs = smooth366(thr)
tdoy = np.array([doyf(x.month, x.day) for x in tgt_dates])
margin = T - thrs[tdoy-1]
nz = margin[np.abs(margin) > 0]
print("min nonzero |margin|: %.3e K  -> hot calls are stable vs ulp-level differences" % np.abs(nz).min())

# active cells per day for the event boundaries (proper 2D handling)
for di, name in [(15,"06-16 end evt1"), (16,"06-17 gap"), (17,"06-18 gap"), (18,"06-19 gap"),
                 (19,"06-20 start evt2"), (50,"07-21 after evt2")]:
    assert str(t_out[di])[:10] == ("2021-%s" % name[:5])
    rows, cols = np.where(mask_out[di] > 0)
    print(name, "active cells:", len(rows), "sample:", list(zip(rows[:6].tolist(), cols[:6].tolist())))

# recompute events straight from the file
active = mask_out.any(axis=(1,2))
ev = []
i = 0
while i < 92:
    if active[i]:
        j = i
        while j+1 < 92 and active[j+1]: j += 1
        ev.append((str(t_out[i])[:10], str(t_out[j])[:10], j-i+1)); i = j+1
    else:
        i += 1
print("events from final file:", ev)
print("total active days:", int(active.sum()))
