
import fsspec
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z')
import re
dates = []
for f in files:
    m = re.search(r'sst_(\d{8})\.nc', f)
    if m:
        dates.append(m.group(1))
dates.sort()
print(f"First: {dates[0]}, Last: {dates[-1]}, Count: {len(dates)}")

# Let's see what date range is covered
import datetime
d1 = datetime.datetime.strptime(dates[0], '%Y%m%d')
d2 = datetime.datetime.strptime(dates[-1], '%Y%m%d')
print(f"Date range: {d1} to {d2}")
