import numpy as np, xarray as xr
z = np.load('/work/interim.npz'); tc = np.load('/work/thr_clim.npz')
sst_t, sst_b, sea, li, oi = z['sst_t'], z['sst_b'], z['sea'], z['li'], z['oi']
thr_s = tc['thr_s']
NC=3600
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
t = ds.time.values
bad_cells = np.where(np.isnan(thr_s[152:245]).any(axis=0).reshape(NC) & sea.reshape(NC))[0]
good_cells = np.where(np.isfinite(thr_s[152:245]).all(axis=0).reshape(NC) & sea.reshape(NC))[0]

for c in [bad_cells[0], good_cells[0]]:
    r, cc = c//60, c%60
    col = ds.analysed_sst.isel(latitude=li[r], longitude=oi[cc]).values.astype(np.float64)  # (15340,)
    out = []
    for y in range(1989, 2016):
        a0 = int(np.searchsorted(t, np.datetime64(f'{y}-01-01','D')))
        a1 = int(np.searchsorted(t, np.datetime64(f'{y+1}-01-01','D')))
        out.append((y, round(float(np.isfinite(col[a0:a1]).mean()), 4)))
    print(f"cell (r={r},c={cc}) lat={li[r]} lon={oi[cc]}")
    print("   ", out)

bb = bad_cells.reshape(-1)
rows = bad_cells // 60; cols = bad_cells % 60
print("bad-cell bounding box: rows", rows.min(), "-", rows.max(), " cols", cols.min(), "-", cols.max())
print("lats:", li[rows.min()], li[rows.max()], "lons:", oi[cols.min()], oi[cols.max()])
# histogram of bad cell rows/cols
import collections
print("rows counts:", dict(sorted(collections.Counter(rows).items())))
print("cols counts:", dict(sorted(collections.Counter(cols).items())))
