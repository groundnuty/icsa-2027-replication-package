
import xarray, numpy as np, pandas as pd
ds=xarray.open_dataset('/work/sst_s2.nc',engine='h5netcdf')
la=ds.latitude.values; lo=ds.longitude.values
ri=np.where((la>=57.13-1e-6)&(la<=58.33+1e-6))[0]; ci=np.where((lo>=22.79-1e-6)&(lo<=23.99+1e-6))[0]
sub=ds.analysed_sst.isel(latitude=ri,longitude=ci).load()
t=sub.time.values
X=sub.values.astype(np.float64)
tgt=(t>=np.datetime64('2014-06-01'))&(t<=np.datetime64('2014-08-31'))
print(t[0],t[-1],len(t),tgt.sum())
fin=np.isfinite(X[tgt]).all(axis=0)
print('sea cells',fin.sum(), 'of', fin.size)
print('nan counts target', np.isnan(X[tgt]).sum(axis=0).min(), np.isnan(X[tgt]).sum(axis=0).max())
print('baseline nan frac over sea cells', np.isnan(X[(t>=np.datetime64('1991-12-27'))&(t<=np.datetime64('2003-01-05'))][:,fin]).mean())
