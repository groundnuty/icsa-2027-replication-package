import xarray as xr
d=xr.open_dataset('/work/sst_20190601.nc',engine='h5netcdf')
print(d.attrs['comment']); print(d.analysed_sst.attrs); print(d.analysed_sst.encoding)
sub=d.analysed_sst.sel(latitude=slice(64.51,65.71),longitude=slice(21.97,23.17))
print(sub.shape, float(sub.min()), float(sub.max()), int(sub.isnull().sum()))