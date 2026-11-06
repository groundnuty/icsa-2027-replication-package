import fsspec,pandas as pd
fs=fsspec.filesystem('onedata');p='icsa2027_data_20261101T090944Z/s1z'
l=fs.ls(p,detail=False);print(len(l))
print(fs.exists(p+'/sst_19920101.nc'),fs.exists(p+'/sst_20100831.nc'),fs.exists(p+'/sst_19911227.nc'),fs.exists(p+'/sst_20030105.nc'))