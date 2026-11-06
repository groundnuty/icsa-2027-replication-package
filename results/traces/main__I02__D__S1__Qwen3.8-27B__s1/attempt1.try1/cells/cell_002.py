import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
# count files and check a sample file size
ls = fs.ls(base)
print("total files:", len(ls))
print("first:", ls[0].split('/')[-1], "last:", ls[-1].split('/')[-1])
import os
# check sizes of a few
for f in ['sst_19911227.nc','sst_19920101.nc','sst_20030101.nc','sst_20030105.nc','sst_20040601.nc','sst_20040831.nc','sst_20021231.nc']:
    try:
        info = fs.info(os.path.join(base,f))
        print(f, info.get('size'))
    except Exception as e:
        print(f, "ERR", e)
