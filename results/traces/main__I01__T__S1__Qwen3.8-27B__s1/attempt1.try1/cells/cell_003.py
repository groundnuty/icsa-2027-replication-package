
import fsspec
fs = fsspec.filesystem('onedata')
base = '/icsa2027_data_20261101T090944Z/s1z/'
test = ['sst_19920101.nc','sst_20080601.nc','sst_20080831.nc','sst_19911227.nc','sst_20030105.nc','sst_20021231.nc','sst_19840927.nc']
for t in test:
    try:
        info = fs.info(base + t)
        print(t, "->", info.get('size'))
    except Exception as e:
        print(t, "-> ERROR:", type(e).__name__, str(e)[:100])
