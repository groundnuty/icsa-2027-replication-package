import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
paths = fs.ls(base)
print("total files:", len(paths))
import re
dates = sorted(re.search(r'sst_(\d{8})\.nc', p).group(1) for p in paths if re.search(r'sst_\d{8}\.nc', p))
print("first:", dates[0], "last:", dates[-1], "count:", len(dates))
# check for any other files
others = [p for p in paths if not re.search(r'sst_\d{8}\.nc', p)]
print("others:", others[:20])
# check the window we need: 1991-12-27 to 2021-08-31
need_start, need_end = '19911227', '20210831'
print("files in needed window:", sum(1 for d in dates if need_start <= d <= need_end))
missing = [d for d in (lambda: None)()]
# find missing days within needed window
import datetime
d0 = datetime.date(1991,12,27); d1 = datetime.date(2021,8,31)
have = set(dates)
miss = []
d = d0
while d <= d1:
    key = d.strftime('%Y%m%d')
    if key not in have: miss.append(key)
    d += datetime.timedelta(days=1)
print("missing days in window:", miss)
