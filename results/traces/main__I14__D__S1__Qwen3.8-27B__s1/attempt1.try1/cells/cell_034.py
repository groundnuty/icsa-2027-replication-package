import numpy as np
from datetime import date
B = np.load('/work/data/B.npy')
T = np.load('/work/data/T.npy')
si = np.load('/work/data/sea_idx.npy')
nsea = len(si)
sea_mask = np.zeros(3600, bool); sea_mask[si] = True
r3 = np.where(sea_mask)[0]
Bsea = B[:, r3//60, r3%60]

# per-cell baseline finite fraction
frac = np.isfinite(Bsea).mean(axis=0)
print("baseline finite fraction per sea cell: min %.4f  median %.4f  max %.4f" % (frac.min(), np.median(frac), frac.max()))
low = np.argsort(frac)[:10]
print("lowest cells (idx, frac, lat, lon):")
for c in low:
    r, cc = r3[c]//60, r3[c]%60
    print("  cell", c, "frac", round(frac[c],4), "lat", B.shape and None)
# print lat/lon from saved
lat = np.load('/work/data/lat_sel.npy'); lon = np.load('/work/data/lon_sel.npy')
for c in low:
    r, cc = r3[c]//60, r3[c]%60
    print("  cell", c, "frac", round(frac[c],4), "lat", lat[r], "lon", lon[cc])

# distribution of pool nvalid for one doy (d=153, June 1)
ENDS = np.cumsum([31,29,31,30,31,30,31,31,30,31,30,31])
def md_of(doy):
    idx = int(np.searchsorted(ENDS, doy, side='left'))
    return idx+1, doy - (int(ENDS[idx-1]) if idx > 0 else 0)
d0 = date(1991,12,27)
from datetime import timedelta
m, dd = md_of(153)
rows = []
for y in range(1992, 2003):
    c = date(y, m, dd)
    for k in range(-5, 6):
        rows.append((c + timedelta(days=k) - d0).days)
rows = np.array(rows)
nv = np.isfinite(Bsea[rows]).sum(axis=0)
print("d=153 pool nvalid: min", nv.min(), "max", nv.max(), " cells with nv<20:", int((nv<20).sum()))
c = int(np.argmin(nv))
r, cc = r3[c]//60, r3[c]%60
print("worst cell for d=153: cell", c, "lat", lat[r], "lon", lon[cc], "nv", nv[c])
# show its baseline finite pattern around June 1 1992 and 2000
for y in [1992, 2000]:
    c0 = (date(y,6,1) - d0).days
    seg = Bsea[c0-5:c0+6, c]
    print(y, np.round(seg, 1))