import fsspec,xarray as xr,os
fs=fsspec.filesystem('onedata')
P='icsa2027_data_20261101T090944Z/s1z/'
for n in ['sst_19920101.nc','sst_20070601.nc','sst_20070831.nc','sst_19911227.nc','sst_20030105.nc']:
    print(n,fs.exists(P+n))