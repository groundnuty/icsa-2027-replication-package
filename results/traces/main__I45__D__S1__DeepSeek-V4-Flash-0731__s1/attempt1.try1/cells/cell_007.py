
import fsspec
fs = fsspec.filesystem('onedata')
# Let's look at s1z more carefully - maybe there are more files beyond the 1000 shown
all_files = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
print("Total in s1z:", len(all_files))

import re
# Group by year
from collections import defaultdict
years = defaultdict(list)
for f in all_files:
    m = re.search(r'sst_(\d{4})(\d{2})(\d{2})\.nc', f)
    if m:
        years[int(m.group(1))].append(m.group(2)+m.group(3))

for y in sorted(years):
    print(f"Year {y}: {len(years[y])} files, months: {sorted(set(d[:2] for d in years[y]))}")
