import numpy as np, xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine="h5netcdf")
t = ds['time'].values
r = t == np.datetime64('1992-07-01')
print("dtype t:", t.dtype, "n True:", r.sum(), "first 10 idx:", np.where(r)[0][:10])
print("direct scalar cmp:", t[0] == np.datetime64('1992-07-01'))
print("cast cmp:", t[0] == np.datetime64('1992-07-01T00:00:00.000000000'))
print("t[3834] cmp:", t[3834] == np.datetime64('1992-07-01T00:00:00.000000000'))
# robust mapping from raw int32
raw = ds['time'].variable.values if hasattr(ds['time'],'variable') else None
import h5py
f = h5py.File('/work/sst_s2.nc','r')
raw = np.asarray(f['time'])
print("raw dtype:", raw.dtype, "raw[0]:", raw[0], "raw[-1]:", raw[-1])
print("seconds/day:", np.all(np.diff(raw)==86400))
ds.close(); f.close()
