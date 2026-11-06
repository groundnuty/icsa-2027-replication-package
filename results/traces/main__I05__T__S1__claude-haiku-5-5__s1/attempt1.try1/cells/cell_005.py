import fsspec
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(base, detail=False)
names=sorted(f.split('/')[-1] for f in files)
print(len(names), names[-1])
for p in ['sst_19920101.nc','sst_20210601.nc','sst_20210831.nc']:
    try:
        print(p, fs.info(base+'/'+p)['size'])
    except Exception as e: print(p, 'ERR', repr(e)[:200])
print(fs.ls('icsa2027_data_20261101T090944Z', detail=False))
