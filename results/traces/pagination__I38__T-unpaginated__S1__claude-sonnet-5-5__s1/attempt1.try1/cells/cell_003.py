import fsspec, xarray as xr
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
fl=fs.ls(p);print(len(fl),fl[-1])
names=sorted(f for f in fl if f.endswith('.nc'));print(len(names),[f for f in fl if not f.endswith('.nc')])
ds=xr.open_dataset(fs.open(names[0],'rb'),engine='h5netcdf');print(ds)