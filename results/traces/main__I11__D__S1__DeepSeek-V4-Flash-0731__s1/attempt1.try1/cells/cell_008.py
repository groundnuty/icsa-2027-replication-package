
import fsspec
fs = fsspec.filesystem('onedata')
# Try to get files with glob
files = fs.glob('icsa2027_data_20261101T090944Z/s1z/*.nc')
print(f"Total glob files: {len(files)}")
# Check years
import re
years = set()
for f in files:
    m = re.search(r'sst_(\d{4})(\d{2})(\d{2})\.nc', f)
    if m:
        years.add(int(m.group(1)))
print(f"Years: {sorted(years)}")
