
import fsspec
fs = fsspec.filesystem('onedata')
base='/icsa2027_data_20261101T090944Z/s1z/'
for name in ['sst_19920101.nc','sst_20021231.nc','sst_20030105.nc','sst_20160601.nc','sst_20160831.nc','sst_19911227.nc','sst_19840927.nc','sst_19860101.nc','sst_20150101.nc']:
    try:
        info = fs.info(base+name)
        print(name, "EXISTS size", info['size'])
    except Exception as e:
        print(name, "MISSING", type(e).__name__)
