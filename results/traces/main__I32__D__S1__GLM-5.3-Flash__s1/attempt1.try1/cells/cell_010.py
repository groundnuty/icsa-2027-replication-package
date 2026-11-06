import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
for d in ['19841231','19851231','19900101','19911227','19911231','19920101','19920601','19991231','20021231','20030105','20050601','20231231']:
    p = f'{base}/sst_{d}.nc'
    try:
        print(d, fs.exists(p), fs.info(p) if fs.exists(p) else '')
    except Exception as e:
        print(d, 'ERR', repr(e)[:100])
