
import fsspec
fs = fsspec.filesystem('onedata')
# Explore s2z
files2 = fs.ls('icsa2027_data_20261101T090944Z/s2z')
print(len(files2))
print(files2[:5])
print(files2[-5:])
import re
dates = []
for f in files2:
    m = re.search(r'sst_(\d{4})(\d{2})(\d{2})\.nc', f)
    if m:
        dates.append((int(m.group(1)), int(m.group(2)), int(m.group(3))))
print("Total files with dates:", len(dates))
if dates:
    years = sorted(set(d[0] for d in dates))
    print("Years:", years)
    print("First:", dates[0], "Last:", dates[-1])
