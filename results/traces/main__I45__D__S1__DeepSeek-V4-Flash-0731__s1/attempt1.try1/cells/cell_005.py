
import fsspec
fs = fsspec.filesystem('onedata')
# Check s2z
files2 = fs.ls('icsa2027_data_20261101T090944Z/s2z')
print("s2z count:", len(files2))
import re
years2 = set()
for f in files2:
    m = re.search(r'sst_(\d{4})(\d{2})(\d{2})\.nc', f)
    if m:
        years2.add(int(m.group(1)))
print("Years in s2z:", sorted(years2))
print("Sample:", files2[:5])
print("Last:", files2[-5:])
