import numpy as np, xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine="h5netcdf")
v = ds['analysed_sst']
print({k: v[k] for k in v.attrs} if hasattr(v,'attrs') else '')
print("encoded:", v.encoding)

# region slice for a few dates
t = ds['time'].values
import datetime
def idx(d): return int((t == np.datetime64(d))[0])
il = np.arange(np.where(ds['latitude'].values >= 61.57-1e-9)[0][0],
               np.where(ds['latitude'].values <= 62.77+1e-9)[0][0]+1)
io = np.arange(np.where(ds['longitude'].values >= 20.17-1e-9)[0][0],
               np.where(ds['longitude'].values <= 21.37+1e-9)[0][0]+1)
s = v.isel(time=[idx('1996-07-01'), idx('2009-07-01'), idx('2009-06-01'), idx('2009-08-31')],
           latitude=il, longitude=io).values
for k, d in enumerate(['1996-07-01','2009-07-01','2009-06-01','2009-08-31']):
    a = s[k]
    fin = a[np.isfinite(a)]
    print(d, "finite:", fin.size, "min/max:", fin.min(), fin.max(),
          "median:", np.median(fin), "n_unique:", len(np.unique(fin)), "273.22 count:", int((a==273.22).sum()))
ds.close()
