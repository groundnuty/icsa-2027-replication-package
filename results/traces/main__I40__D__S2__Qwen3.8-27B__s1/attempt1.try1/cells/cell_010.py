import numpy as np, xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine="h5netcdf")
v = ds['analysed_sst']
t = ds['time'].values
def idx(d): return int((t == np.datetime64(d))[0])
la = ds['latitude'].values; lo = ds['longitude'].values
il = np.arange(int(np.where(la >= 61.57-1e-9)[0][0]), int(np.where(la <= 62.77+1e-9)[0][0])+1)
io = np.arange(int(np.where(lo >= 20.17-1e-9)[0][0]), int(np.where(lo <= 21.37+1e-9)[0][0])+1)
print("il:", il[0], il[-1], " io:", io[0], io[-1])
for d in ['1996-07-01','2009-07-01','2009-06-01','2009-08-31','2009-07-15','1995-01-15','2001-01-15']:
    a = v.isel(time=idx(d), latitude=il, longitude=io).values
    fin = a[np.isfinite(a)]
    print(d, "finite:", fin.size, "of", a.size,
          ("min/max: %.2f/%.2f med %.2f uniq %d" % (fin.min(), fin.max(), np.median(fin), len(np.unique(fin)))) if fin.size else "")
# 2D view for 2009-07-15
a = v.isel(time=idx('2009-07-15'), latitude=il, longitude=io).values
with np.printoptions(linewidth=200, precision=2, suppress=False):
    print(np.where(np.isfinite(a), a, np.nan))
ds.close()
