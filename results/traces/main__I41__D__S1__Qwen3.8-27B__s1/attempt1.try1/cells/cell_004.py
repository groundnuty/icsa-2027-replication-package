import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
# check if ls returns everything; try to get a later file explicitly
for d in ['sst_20210601.nc','sst_20210831.nc','sst_20210901.nc','sst_20020101.nc','sst_20030105.nc','sst_19911227.nc','sst_20260101.nc']:
    p = base + '/' + d
    try:
        info = fs.info(p)
        print(d, "OK", info.get('size'))
    except Exception as e:
        print(d, "ERR", str(e)[:120])
