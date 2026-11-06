import fsspec
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z/'
for n in ['sst_19911231.nc','sst_19920101.nc','sst_19950601.nc','sst_20000101.nc','sst_20120601.nc','sst_20120831.nc','sst_19840927.nc']:
    try: print(n, fs.exists(base+n))
    except Exception as e: print(n, 'ERR', e)
print(fs.ls(base, detail=False)[-3:])