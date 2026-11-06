import fsspec
fs = fsspec.filesystem('onedata')
base='/icsa2027_data_20261101T090944Z/s1z'
# probe specific files
for probe in ['sst_19920101.nc','sst_20021231.nc','sst_20030601.nc','sst_20090601.nc','sst_20090831.nc','sst_19910227.nc','sst_20030105.nc']:
    p=f'{base}/{probe}'
    try:
        info=fs.info(p)
        print(probe,'EXISTS size',info.get('size'))
    except Exception as ex:
        print(probe,'MISSING',repr(ex)[:120])
# size of an early file
info=fs.info(f'{base}/sst_19820101.nc')
print('early file size:', info.get('size'))
