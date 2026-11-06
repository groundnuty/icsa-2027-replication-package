import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print(ds.analysed_sst.attrs)
print('encoding:', {k:v for k,v in ds.analysed_sst.encoding.items() if k in ('dtype','_FillValue','scale_factor','add_offset')})
print('time encoding:', ds.time.encoding)
