import numpy as np, fsspec, xarray as xr
from datetime import date
z = np.load('work/sst.npz')
ST = z['ST']; tt = z['tt']; SB = z['SB']; tb = z['tb']
z2 = np.load('work/thr.npz')
sea, thr_s = z2['sea'], z2['thr_s']
n_cells = 3600
lat, lon = z['lat'], z['lon']

# 1) independent re-read of 2004-08-01 and 2004-07-31 for the region
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
dlat = ds.latitude.values; dlon = ds.longitude.values; dt = ds.time.values
eps = 1e-6
li = np.where((dlat >= 54.17-eps) & (dlat <= 55.37+eps))[0]
lo = np.where((dlon >= 13.25-eps) & (dlon <= 14.45+eps))[0]
def idx(ts): return int(np.searchsorted(dt, np.datetime64(ts)))
for dstr, tname in [('2004-08-01','ST'), ('2004-07-31','ST'), ('1996-07-17','SB')]:
    i = idx(dstr)
    if tname == 'ST':
        rel = i - idx('2004-06-01')
        ref = ST[rel].astype(np.float64)
    else:
        rel = i - idx('1991-12-27')
        ref = SB[rel].astype(np.float64)
    fresh = ds['analysed_sst'].isel(time=i, latitude=slice(int(li[0]), int(li[-1])+1), longitude=slice(int(lo[0]), int(lo[-1])+1)).values.astype(np.float64)
    d = fresh - ref
    print(dstr, "max |diff|:", np.abs(d).max(), "equal frac:", float((d == 0).mean()))

# 2) the 297 empty-pool cells: where are they? how much baseline data do they have?
SBf = SB.reshape(4028, n_cells)
finite_per_cell_baseline = np.isfinite(SBf).sum(axis=0)
empty = np.isnan(thr_s).any(axis=1) & sea
print("empty-pool sea cells:", int(empty.sum()))
print("their baseline finite days: min", finite_per_cell_baseline[empty].min(), "max", finite_per_cell_baseline[empty].max())
ys = np.argwhere(empty.reshape(60, 60))
print("lat range of empty cells:", lat[ys[:,0]].min(), lat[ys[:,0]].max(), "| lon:", lon[ys[:,1]].min(), lon[ys[:,1]].max())
# how many are strictly at coast (adjacent to a land cell)?
land = ~sea
edge = np.zeros_like(sea)
for dy in (-1,0,1):
    for dx in (-1,0,1):
        edge |= np.roll(np.roll(land, dy, axis=0), dx, axis=1)
print("of empty cells, fraction adjacent to land:", float(edge[empty].mean()))
# target finite days for these cells
STf = ST.reshape(92, n_cells)
print("their target finite days:", np.unique(np.isfinite(STf[:, empty]).sum(axis=0)))
