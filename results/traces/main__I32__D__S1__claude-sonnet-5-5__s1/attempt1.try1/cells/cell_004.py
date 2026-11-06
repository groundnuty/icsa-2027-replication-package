import fsspec,re,datetime as dt
fs=fsspec.filesystem('onedata')
P='icsa2027_data_20261101T090944Z/s1z/'
names=sorted(f.split('/')[-1] for f in fs.ls(P))
print(len(names))
try:
    n2=fs.ls(P,detail=False); print(len(n2))
except Exception as e: print(e)
print(fs.exists(P+'sst_20050601.nc'), fs.exists(P+'sst_20051231.nc'),fs.exists(P+'sst_20060101.nc'),fs.exists(P+'sst_19911227.nc'))