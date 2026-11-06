import fsspec,os,xarray as xr
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
fl=fs.ls(p,detail=False)
print(len(fl),fl[-1])
fs.get(fl[0],'/work/a.nc')
d=xr.open_dataset('/work/a.nc',engine='h5netcdf');print(d)