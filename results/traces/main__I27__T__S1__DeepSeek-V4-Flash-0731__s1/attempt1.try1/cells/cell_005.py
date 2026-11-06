
import fsspec
import re
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s2z')
print(len(files))
print(files[:5])
print(files[-5:])
dates = []
for f in files:
    m = re.search(r'sst_(\d{4})(\d{2})(\d{2})\.nc', f)
    if m:
        dates.append((int(m.group(1)), int(m.group(2)), int(m.group(3))))
years = sorted(set(d[0] for d in dates))
print("Years:", years)
print("Number of dates:", len(dates))
print("First:", dates[0], "Last:", dates[-1])
