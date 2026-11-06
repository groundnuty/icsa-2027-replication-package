
import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(base)
print(f"Total files: {len(files)}")

import re
years = {}
for f in files:
    m = re.search(r'sst_(\d{4})(\d{2})(\d{2})\.nc', f.split('/')[-1])
    if m:
        y = m.group(1)
        years.setdefault(y, []).append(f)

for y in sorted(years.keys()):
    print(f"{y}: {len(years[y])} files")
