
import fsspec
fs = fsspec.filesystem('onedata')

# Let me check what's in the s1z directory - maybe there's a metadata file or description
all_files = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
print(len(all_files))

# Check if any files are not the daily SST files
non_sst = [f for f in all_files if 'sst_' not in f]
print("Non-sst files:", non_sst)

# Check the daily files structure more carefully
import re
# Find the full date range
dates = []
for f in all_files:
    m = re.search(r'sst_(\d{4})(\d{2})(\d{2})\.nc', f)
    if m:
        dates.append((int(m.group(1)), int(m.group(2)), int(m.group(3))))
dates.sort()
print("First date:", dates[0])
print("Last date:", dates[-1])
print("Count:", len(dates))
