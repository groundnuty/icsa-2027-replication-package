import numpy as np
print('numpy', np.__version__)
# verify hazen = type 5
a = np.array([1.,2.,3.,4.])
print('hazen q0.9:', np.nanquantile(a, 0.9, method='hazen'))  # expect 1+0.9*3 = 3.7
import fsspec, xarray as xr
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','rb')
ds = xr.open_dataset(f, engine="h5netcdf")
t = ds['time'].values
i0 = np.searchsorted(t, np.datetime64('2014-06-01')); i1 = np.searchsorted(t, np.datetime64('2014-08-31'))
print('target window:', t[i0], t[i1], 'n =', i1-i0+1)
print('contiguous:', np.all(np.diff(t[i0:i1+1]) == np.timedelta64(1,'D')))
j0 = np.searchsorted(t, np.datetime64('1991-12-27')); j1 = np.searchsorted(t, np.datetime64('2003-01-05'))
print('baseline window:', t[j0], t[j1], 'n =', j1-j0+1)
print('contiguous:', np.all(np.diff(t[j0:j1+1]) == np.timedelta64(1,'D')))
ds.close(); f.close()
