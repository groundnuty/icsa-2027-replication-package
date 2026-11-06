import numpy as np, pandas as pd

# 1. verify map_doy
CUM = np.array([0,31,59,90,120,151,181,212,243,273,304,334])
def map_doy(ts):
    return int(CUM[ts.month-1] + ts.day + (1 if ts.month > 2 else 0))
tests = [('1992-02-28',59),('1992-02-29',60),('1992-03-01',61),('1992-12-31',366),
         ('1993-02-28',59),('1993-03-01',61),('1993-12-31',365),('1992-01-01',1),
         ('2012-06-01',153),('2012-08-31',244),('2012-08-15',228),('2012-08-19',232),
         ('2000-02-29',60),('2001-02-28',59),('2001-03-01',61)]
ok = True
for s, exp in tests:
    got = map_doy(pd.Timestamp(s))
    if got != exp: ok=False; print("MISMATCH", s, got, exp)
print("map_doy all correct:", ok)

# 2. hazen (type 5) sanity vs manual formula: sorted x, h=(n*0.9)+0.5, q = x[floor h]+ (h-floor h)*(x[ceil h]-x[floor h])
rng = np.random.default_rng(0)
for n in [7, 121, 1000]:
    x = rng.normal(size=(n,3))
    q = np.percentile(x, 90, axis=0, method='hazen')
    xs = np.sort(x, axis=0)
    h = 0.9*n + 0.5
    lo = int(np.floor(h)); frac = h - lo
    m = xs[np.minimum(lo-1, n-1)] + frac*(xs[np.minimum(lo, n-1)] - xs[np.minimum(lo-1, n-1)])
    print(f"n={n}: hazen matches manual:", bool(np.allclose(q, m)))

# 3. spatial pattern of the 26 MHW cells
z = np.load('/work/final.npz')
per_cell, sea = z['per_cell'], z['sea']
lat = np.arange(438,498)*0.02 + 53.5
lon = np.arange(487,547)*0.02 + 9.0
# exact: recompute from dataset coords
import h5py
f = h5py.File('/work/sst_s2.nc','r')
LAT = f['latitude'][438:498]; LON = f['longitude'][487:547]
mhw_cells = per_cell[75].copy()   # 2012-08-15
print("cells in MHW on Aug15:", int(mhw_cells.sum()))
rows = np.where(mhw_cells.any(axis=1))[0]; cols = np.where(mhw_cells.any(axis=0))[0]
print("lat extent:", LAT[rows.min()], "-", LAT[rows.max()], "lon extent:", LON[cols.min()], "-", LON[cols.max()])
print("contiguous block:", bool(mhw_cells[rows.min():rows.max()+1, cols.min():cols.max()+1].all() == mhw_cells[rows.min():rows.max()+1, cols.min():cols.max()+1].sum() == mhw_cells.sum()))
# print a compact map (rows with cells)
print("MHW cell map (# = in MHW, . = sea not in MHW, ' ' = land):")
for i in range(rows.min(), rows.max()+1):
    line = "".join('#' if mhw_cells[i,j] else ('.' if sea[i,j] else ' ') for j in range(60))
    print(f"  {LAT[i]:.2f}N {line}")
