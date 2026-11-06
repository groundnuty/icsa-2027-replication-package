import os
from collections import Counter
base = "/data/icsa2027_data_20261101T090944Z/s1z"
files = sorted(f for f in os.listdir(base) if f.startswith("sst_") and f.endswith(".nc"))
print("count:", len(files))
print("first:", files[0], "last:", files[-1])
years = Counter(f[4:8] for f in files)
print("by year:", dict(sorted(years.items())))
