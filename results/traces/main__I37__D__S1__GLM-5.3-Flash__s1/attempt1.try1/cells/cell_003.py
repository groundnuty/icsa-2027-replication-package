import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
# check a few specific files exist
for name in ['sst_19920601.nc','sst_20020831.nc','sst_20120601.nc','sst_20120831.nc','sst_19911227.nc','sst_20030105.nc']:
    p = f'{base}/{name}'
    try:
        info = fs.info(p)
        print(name, info.get('size'), info.get('type'))
    except Exception as e:
        print(name, "ERROR", type(e).__name__, str(e)[:120])
