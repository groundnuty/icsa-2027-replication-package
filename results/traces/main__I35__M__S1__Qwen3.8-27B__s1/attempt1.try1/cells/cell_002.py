import os
base = "/data/icsa2027_data_20261101T090944Z/s1z"
files = [f for f in os.listdir(base) if f.startswith("sst_")]
import re
dates = sorted(re.match(r"sst_(\d{8})\.nc", f).group(1) for f in files)
print("num files:", len(dates))
print("first:", dates[:3], "last:", dates[-3:])
