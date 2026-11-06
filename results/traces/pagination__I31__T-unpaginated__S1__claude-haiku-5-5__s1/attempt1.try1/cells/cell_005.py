
import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
ds=xr.open_dataset(fs.open(p,'rb'),engine='h5netcdf')
v=ds['analysed_sst']; print(v.attrs); print(v.encoding); print(ds.attrs['comment'])
a=v.values; print(np.nanmin(a),np.nanmax(a), np.isnan(a).sum(), a.size)
print(ds.latitude.values[[0,-1]], ds.longitude.values[[0,-1]])
