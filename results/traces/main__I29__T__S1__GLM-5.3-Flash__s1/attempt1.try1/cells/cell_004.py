import xarray as xr, fsspec, numpy as np
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
print(ds)
print(ds.sst.encoding.get('dtype'), ds.sst.encoding.get('_FillValue'))
