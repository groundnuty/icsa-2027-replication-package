import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
items = fs.ls(base)
print("total files:", len(items))
# find min and max dates
import re
dates = sorted(set(x.split('/')[-1][4:12] for x in items if x.split('/')[-1].startswith('sst_') and x.split('/')[-1].endswith('.nc')))
print("first:", dates[0], "last:", dates[-1], "count:", len(dates))
