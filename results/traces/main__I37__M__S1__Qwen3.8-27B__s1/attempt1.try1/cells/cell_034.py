import time, datetime as dt, json, warnings
import numpy as np

t0 = time.time()
ext = np.load('/work/chk/ext.npy').astype(np.float64)
sea = np.load('/work/chk/sea.npy')

def daterange(a, b):
    d, out = a, []
    while d <= b:
        out.append(d); d += dt.timedelta(days=1)
    return out
ext_dates = daterange(dt.date(1991,12,27), dt.date(2003,1,5))
doy_ext = np.array([dt.date(2000, d.month, d.day).timetuple().tm_yday for d in ext_dates])
doy_b = doy_ext[5:5+4018]

# hazen formula probe (for the record)
x = np.arange(1, 6)
for q in (0.5, 0.9, 0.99):
    print("hazen n=5 q=", q, "->", np.quantile(x, q, method='hazen'), "| linear:", np.quantile(x, q, method='linear'))

# empty-pool map per doy
empty = np.zeros((366, 60, 60), bool)
minsize = np.zeros((366, 60, 60), int)
for d in range(1, 367):
    if d == 60:
        continue
    js = np.where(doy_b == d)[0]
    rows = (5 + js[:, None] + np.arange(-5, 6)[None, :]).ravel()
    pool = ext[rows]
    nv = np.isfinite(pool).sum(axis=0)
    minsize[d-1] = nv
    empty[d-1] = (nv == 0)
sea2d = sea
empty_sea = empty & sea2d[None, :, :]
print("empty (d,cell) pairs among sea cells:", int(empty_sea.sum()), " over", 365*sea2d.sum())
# per sea cell: which doys empty
cell_empty_doys = empty_sea.any(axis=(1,2))
print("doys with >=1 empty sea-cell pool:", np.where(cell_empty_doys)[0].tolist())
# cells with any empty pool
cells_any = empty_sea.any(axis=0)
print("sea cells with any empty pool:", int(cells_any.sum()))
# do the smoothed-NaN bands reach target doy 153..244?
# smoothed thr at d is NaN for a cell if any of d-15..d+15 (mod 366) is empty (raw) for that cell
band = np.zeros((366, 60, 60), bool)
for k in range(-15, 16):
    band |= np.roll(empty_sea, -k, axis=0)
target_hit = band[153-1:244, :, :].any(axis=0)
print("sea cells whose target-period smoothed threshold is NaN:", int(target_hit.sum()))
np.save('/work/chk/empty.npy', empty)
print("done in", time.time()-t0)
