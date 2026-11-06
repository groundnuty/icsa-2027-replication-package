import numpy as np, xarray as xr
z = np.load('/work/interim.npz'); tc = np.load('/work/thr_clim.npz')
sst_t, sst_b, sea, li, oi = z['sst_t'], z['sst_b'], z['sea'], z['li'], z['oi']
thr, clim, thr_s = tc['thr'], tc['clim'], tc['thr_s']
NC=3600
origin = np.datetime64('1991-12-27','D')

# yearly finiteness for an affected cell and a normal sea cell
t = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf').time.values
def i64(d): return int(np.searchsorted(t, np.datetime64(d,'D')))
bad_cells = np.where(np.isnan(thr_s[152:245]).any(axis=0).reshape(NC) & sea.reshape(NC))[0]
good_cells = np.where(np.isfinite(thr_s[152:245]).all(axis=0).reshape(NC) & sea.reshape(NC))[0]
print("bad sea cells:", len(bad_cells), " good sea cells:", len(good_cells))
for c in [bad_cells[0], good_cells[0]]:
    r, cc = c//60, c%60
    yrs = {}
    for y in [1990,1991,1992,1995,1999,2001,2002,2003,2005,2010,2013,2014,2015,2020]:
        a0 = i64(f'{y}-01-01'); a1 = i64(f'{y+1}-01-01')
        col = sst_b[a0-5:a1-5] if a0>=5 and a1<=sst_b.shape[0] else None
        if col is None:
            ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
            col = ds.analysed_sst.isel(time=slice(a0,a1), latitude=li[r], longitude=oi[cc]).values
        yrs[y] = np.isfinite(col).mean()
    print(f"cell (r={r},c={cc}) lat={li[r]} lon={oi[cc]}: finiteness by year:", {y: round(v,3) for y,v in yrs.items()})

# where are bad cells? print bounding box and some coords
bb = bad_cells.reshape(60,60)
rows, cols = np.where(bb)
print("bad-cell bounding box: lat rows", rows.min(), "-", rows.max(), " lon cols", cols.min(), "-", cols.max())
print("example coords:", [(li[r], oi[c]) for r,c in list(zip(rows,cols))[:10]])

# cross-validate hazen implementation vs np.nanquantile on random pools from data
import warnings
def hazen90_cols(A):
    n = np.isfinite(A).sum(axis=0)
    S = np.sort(A, axis=0)
    out = np.full(A.shape[1], np.nan)
    ok = n > 0
    v = 0.9*n[ok] - 0.5
    vm = np.clip(v, 0.0, n[ok]-1)
    j = np.floor(vm).astype(np.int64)
    jj = np.clip(j+1, 0, n[ok]-1)
    g = vm - j
    cols = np.arange(n[ok].size)
    out[ok] = S[j, cols] + g*(S[jj, cols] - S[j, cols])
    return out
rng = np.random.default_rng(42)
maxdiff = 0.0
for trial in range(200):
    W = rng.integers(1, 130)
    A = rng.normal(288, 2, (W, 50))
    # sprinkle NaNs
    A[rng.random((W,50)) < 0.05] = np.nan
    mine = hazen90_cols(A)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        ref = np.nanquantile(A, 0.9, method='hazen', axis=0)
    d = np.nanmax(np.abs(mine - ref))
    maxdiff = max(maxdiff, d)
print("max |mine - nanquantile| over 200 random pools:", maxdiff)
