import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
for name in ['sst_19920101.nc','sst_20190601.nc','sst_20030105.nc','sst_19840927.nc','sst_20251231.nc']:
    try:
        info = fs.info(base + '/' + name)
        print(name, "EXISTS", {k:info.get(k) for k in ('size',) if k in info})
    except Exception as e:
        print(name, "ERR", type(e).__name__, str(e)[:120])
