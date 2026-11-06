
import fsspec
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z')
print(len(files))
print(files[0])
print(files[-1])
# Parse dates from filenames
import re
dates = []
for fp in files:
    name = fp.split('/')[-1]
    m = re.match(r'sst_(\d{4})(\d{2})(\d{2})\.nc', name)
    if m:
        dates.append((int(m.group(1)), int(m.group(2)), int(m.group(3))))
print('First date:', dates[0])
print('Last date:', dates[-1])
print('Number of dates:', len(dates))
# Check range
all_dates = sorted(dates)
print('Date range:', all_dates[0], all_dates[-1])
