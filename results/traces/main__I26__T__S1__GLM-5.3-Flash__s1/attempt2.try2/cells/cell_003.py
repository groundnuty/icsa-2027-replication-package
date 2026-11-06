import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
for d in ['19820101','19840927','19840928','19911227','19911231','19920101','20021231','20030101','20030105','20030601','20070601','20070831','20071231']:
    p = f'{base}/sst_{d}.nc'
    try:
        ex = fs.exists(p)
        print(d, ex)
    except Exception as e:
        print(d, 'ERR', type(e).__name__, e)
