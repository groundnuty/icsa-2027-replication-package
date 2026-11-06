import fsspec,os,xarray as xr
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
for pat in ['sst_19920101.nc','sst_20130601.nc','sst_20021231.nc']:print(pat, fs.exists(p+'/'+pat))
print(fs.ls(p+'/..',detail=False)[:20])