
import os
files = sorted(os.listdir('/data/icsa2027_data_20261101T090944Z/s1z'))
years = set()
for f in files:
    # sst_YYYYMMDD.nc
    y = f[4:8]
    years.add(int(y))
print(sorted(years))
print(f"Total files: {len(files)}")
