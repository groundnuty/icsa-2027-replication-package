import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
# probe specific files we need
probes = ['sst_19920101.nc','sst_20021231.nc','sst_20031231.nc','sst_20210601.nc','sst_20210831.nc','sst_19911231.nc','sst_19911227.nc']
for p in probes:
    path = f"{base}/{p}"
    try:
        info = fs.info(path)
        print("EXISTS", p, info.get('size'))
    except Exception as ex:
        print("MISSING", p, type(ex).__name__, str(ex)[:120])
# try find to see whether ls is truncated
try:
    found = fs.find(base)
    print("find count:", len(found))
except Exception as ex:
    print("find failed:", type(ex).__name__, str(ex)[:200])
