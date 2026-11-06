import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
for name in ['sst_20130601.nc','sst_20130831.nc','sst_19930101.nc','sst_20021231.nc','sst_20030101.nc','sst_19911227.nc','sst_19920229.nc']:
    try:
        i = fs.info(f'{base}/{name}')
        print(name, i.get('size'), i.get('type'))
    except Exception as e:
        print(name, "ERR", type(e).__name__, str(e)[:100])
