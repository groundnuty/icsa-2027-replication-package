import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
for name in ['sst_19911227.nc','sst_20021231.nc','sst_20030105.nc','sst_20210601.nc','sst_20210831.nc']:
    try:
        info = fs.info(f'{base}/{name}')
        print(name, "EXISTS", info.get('size'))
    except Exception as e:
        print(name, "MISSING:", type(e).__name__, e)
