import fsspec
fs = fsspec.filesystem('onedata')
p = 'icsa2027_data_20261101T090944Z/s1z'
# Check whether specific files exist beyond the listed range
for f in ['sst_19920601.nc','sst_19921231.nc','sst_20020101.nc','sst_20031231.nc','sst_20170601.nc','sst_20170831.nc','sst_20180101.nc']:
    path = p + '/' + f
    try:
        info = fs.info(path)
        print(f, info.get('size'))
    except Exception as ex:
        print(f, 'MISSING', type(ex).__name__)
