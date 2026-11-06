import numpy as np, xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine="h5netcdf")
v = ds['analysed_sst']
t = ds['time'].values
def idx(d): return int((t == np.datetime64(d))[0])
il = np.arange(404, 464); io = np.arange(559, 619)
for d in ['1996-07-01','2009-07-01','2009-06-01','2009-08-31','2009-07-15','1995-01-15','2001-01-15']:
    a = v.isel(time=idx(d), latitude=il, longitude=io).values
    fin = a[np.isfinite(a)]
    print(d, "finite:", fin.size, "of", a.size,
          ("min/max: %.2f/%.2f med %.2f uniq %d" % (fin.min(), fin.max(), np.median(fin), len(np.unique(fin)))) if fin.size else "")
a = v.isel(time=idx('2009-07-15'), latitude=il, longitude=io).values
np.set_printoptions(linewidth=250, precision=2)
print(a)
ds.close()
