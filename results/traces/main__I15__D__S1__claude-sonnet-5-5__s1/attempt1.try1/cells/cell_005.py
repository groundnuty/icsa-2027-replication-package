import fsspec,re
fs=fsspec.filesystem('onedata')
P='icsa2027_data_20261101T090944Z/s1z/'
print(fs.exists(P+'sst_19920101.nc'),fs.exists(P+'sst_20190601.nc'))
fl=fs.ls(P,detail=False);print(len(fl))
try:
  f=fs.find(P);print(len(f))
except Exception as e:print(e)
try:
  g=fs.glob(P+'sst_2019*.nc');print(len(g))
except Exception as e:print(e)