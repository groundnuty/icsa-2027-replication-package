import fsspec,os,xarray as xr
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
fs.get(p+'/sst_19911227.nc','/work/t.nc')
d=xr.open_dataset('/work/t.nc',engine='h5netcdf')
print(d.analysed_sst.attrs, d.analysed_sst.encoding.get('dtype'))
d=d.sel(latitude=slice(57.405,58.615),longitude=slice(18.685,19.895));print(d.sizes)