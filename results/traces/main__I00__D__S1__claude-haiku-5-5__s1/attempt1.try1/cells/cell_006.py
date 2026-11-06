import fsspec, os, time, xarray as xr
ds=xr.open_dataset('/work/d/sst_19920101.nc',engine='h5netcdf')
print(ds.analysed_sst.attrs); print(ds.analysed_sst.encoding)
print(ds.attrs['comment'])
t=time.time(); fs=fsspec.filesystem('onedata'); fs.get('icsa2027_data_20261101T090944Z/s1z/sst_19920102.nc','/work/d/sst_19920102.nc'); print(time.time()-t)
