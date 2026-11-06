import fsspec, re, xarray, time, os
fs = fsspec.filesystem('onedata')
P='icsa2027_data_20261101T090944Z/s1z/'
f=fs.open(P+'sst_20120601.nc','rb')
d2=xarray.open_dataset(f,engine='h5netcdf')
print(d2.analysed_sst.attrs); print(d2.analysed_sst.encoding)
print(d2.latitude.values[:3], d2.latitude.values[-3:], d2.longitude.values[:3], d2.longitude.values[-3:])
import numpy as np
a=d2.analysed_sst.values[0]
sub=a[(d2.latitude.values>=54.45)&(d2.latitude.values<=55.65)][:, (d2.longitude.values>=16.05)&(d2.longitude.values<=17.25)]
print(sub.shape, np.isfinite(sub).sum(), np.nanmin(sub), np.nanmax(sub))