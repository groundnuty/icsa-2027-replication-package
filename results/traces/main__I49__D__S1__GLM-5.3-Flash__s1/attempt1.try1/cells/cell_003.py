import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
probes = ['sst_19920101.nc','sst_20021231.nc','sst_20190601.nc','sst_20190831.nc','sst_19840927.nc','sst_19821001.nc']
for p in probes:
    try:
        info = fs.info(f'{base}/{p}')
        print(p, "EXISTS", info.get('size'))
    except Exception as ex:
        print(p, "missing:", type(ex).__name__)
