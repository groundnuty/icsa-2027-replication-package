import numpy as np
z = np.load('/work/interim.npz'); tc = np.load('/work/thr_clim.npz')
sst_t, sst_b, sea, li, oi = z['sst_t'], z['sst_b'], z['sea'], z['li'], z['oi']
thr, thr_s = tc['thr'], tc['thr_s']
NC = 3600
origin = np.datetime64('1991-12-27','D')
def d2i(d64): return int((d64 - origin) // np.timedelta64(1,'D'))

# 1) are empty-pool cells exactly the non-sea cells?
def doy_to_md(d):
    leap = d >= 61
    days = [31,29,31,30,31,30,31,31,30,31,30,31] if leap else [31,28,31,30,31,30,31,31,30,31,30,31]
    for m, nd in enumerate(days):
        if d <= nd: return m+1, d
        d -= nd

empty_any = np.zeros(NC, bool)
nanfrac_sum = np.zeros(NC)
for d in range(1, 367):
    if d == 60: continue
    m, dd = doy_to_md(d)
    sl = []
    for y in range(1992, 2003):
        bi = d2i(np.datetime64(f'{y:04d}-{m:02d}-{dd:02d}','D'))
        sl.append(sst_b[bi-5:bi+6])
    A = np.concatenate(sl, axis=0).reshape(121, NC)
    nfin = np.isfinite(A).sum(axis=0)
    empty_any |= (nfin == 0)
    nanfrac_sum += np.where(nfin>0, (121-nfin)/121, 1.0)
print("cells with >=1 empty pool:", int(empty_any.sum()))
print("non-sea cells:", int((~sea).sum()), " identical set:", bool(np.array_equal(empty_any, (~sea).reshape(NC))))

# 2) sea cells with any NaN in smoothed target threshold
td = slice(152,245)
bad = np.isnan(thr_s[td]).any(axis=0).reshape(60,60)
print("cells with NaN smoothed thr over target days:", int(bad.sum()))
print("  of which non-sea:", int((bad & ~sea).sum()))
sea_bad = np.where(bad & sea)
print("  sea cells affected:", len(sea_bad[0]))

# 3) for the affected sea cells, look at empty pools in the raw (unsmoothed) threshold
if len(sea_bad[0])>0:
    flat_cells = np.where((bad & sea).reshape(NC))[0]
    for c in flat_cells[:5]:
        empt = [d for d in range(1,367) if d!=60 and np.isnan(thr[d-1].reshape(NC)[c])]
        print("cell", c, "(r=%d,c=%d)" % (c//60, c%60), "empty raw-thr doys:", len(empt), empt[:40])
