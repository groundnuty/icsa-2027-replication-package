import fsspec
fs=fsspec.filesystem('onedata')
d='icsa2027_data_20261101T090944Z/s1z'
for p in ['sst_20210601.nc','sst_19911227.nc','sst_20030105.nc']:
    print(p,fs.exists(d+'/'+p))
r=fs.ls(d,detail=False);print(len(r))
import inspect;print(inspect.signature(fs.ls))
print([a for a in dir(fs) if not a.startswith('_')][:80])