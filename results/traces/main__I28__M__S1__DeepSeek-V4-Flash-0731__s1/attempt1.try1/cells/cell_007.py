
import os
files = sorted(os.listdir('/data/icsa2027_data_20261101T090944Z/s1z'))
print("Total files:", len(files))
# Check what dates are available
import re
dates = []
for f in files:
    m = re.match(r'sst_(\d{8})\.nc', f)
    if m:
        dates.append(m.group(1))
print("First 10 dates:", dates[:10])
print("Last 10 dates:", dates[-10:])
print("Date range:", dates[0], "to", dates[-1])
