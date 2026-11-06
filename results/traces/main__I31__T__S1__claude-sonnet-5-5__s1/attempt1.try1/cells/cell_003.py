import fsspec,xarray as xr
fs=fsspec.filesystem('onedata')
D='icsa2027_data_20261101T090944Z/s1z/'
r=fs.ls(D,detail=False)
print(len(r),r[-1])
for p in ['sst_19911227','sst_20030105','sst_20170601','sst_20170831']:
    print(p,fs.exists(f'{D}{p}.nc'))
ds=xr.open_dataset(fs.open(D+'sst_20170601.nc','rb'),engine='h5netcdf');print(ds)