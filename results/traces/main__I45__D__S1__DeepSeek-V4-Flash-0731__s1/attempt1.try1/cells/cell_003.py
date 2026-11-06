
import fsspec
fs = fsspec.filesystem('onedata')
# List all files
all_files = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
print("Total files:", len(all_files))

import re
years = set()
months = {}
for f in all_files:
    m = re.search(r'sst_(\d{4})(\d{2})(\d{2})\.nc', f)
    if m:
        y = int(m.group(1))
        mo = int(m.group(2))
        years.add(y)
        months.setdefault(y, set()).add(mo)

print("Years:", sorted(years))
for y in sorted(years):
    print(f"  Year {y}: months {sorted(months[y])}, count = {len([f for f in all_files if f'sst_{y}' in f])}")
