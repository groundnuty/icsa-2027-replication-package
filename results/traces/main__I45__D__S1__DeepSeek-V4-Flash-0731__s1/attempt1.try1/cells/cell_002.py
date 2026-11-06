
import fsspec
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z')
print("Number of files:", len(files))
# Get a sample of file names
import re
years = set()
for f in files:
    m = re.search(r'sst_(\d{4})(\d{2})(\d{2})\.nc', f)
    if m:
        years.add(int(m.group(1)))
print("Years:", sorted(years))
