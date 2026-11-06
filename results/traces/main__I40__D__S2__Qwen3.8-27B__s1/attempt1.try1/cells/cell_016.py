import numpy as np, xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine="h5netcdf")
v = ds['analysed_sst']
t = ds['time'].values
def idx(d): return int((t == np.datetime64(d))[0])
a = v.isel(time=idx('1992-01-01')).values
b = v.isel(time=idx('1992-07-01')).values
print("a range:", a[np.isfinite(a)].min(), a[np.isfinite(a)].max())
print("b range:", b[np.isfinite(b)].min(), b[np.isfinite(b)].max())
fin_a = np.isfinite(a); fin_b = np.isfinite(b)
both = fin_a & fin_b
diff = both & (a != b)
print("both finite:", both.sum(), "differing:", diff.sum())
print("a finite b nan:", (fin_a & ~fin_b).sum(), "a nan b finite:", (~fin_a & fin_b).sum())
# spatial pattern of differences
ys, xs = np.where(diff)
print("diff rows lat range:", ds['latitude'].values[ys.min()], ds['latitude'].values[ys.max()],
      "cols lon:", ds['longitude'].values[xs.min()], ds['longitude'].values[xs.max()])
# sample some diff values
print("a samples:", a[ys[:5], xs[:5]], " b samples:", b[ys[:5], xs[:5]])
ds.close()
