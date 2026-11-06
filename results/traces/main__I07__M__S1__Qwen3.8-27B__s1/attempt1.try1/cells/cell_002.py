import os, re
base = "/data/icsa2027_data_20261101T090944Z/s1z"
files = sorted(os.listdir(base))
pat = re.compile(r"^sst_(\d{8})\.nc$")
dates = []
other = []
for f in files:
    m = pat.match(f)
    if m:
        dates.append(m.group(1))
    else:
        other.append(f)
print("num daily files:", len(dates))
print("min:", min(dates), "max:", max(dates))
print("other files:", other[:10], len(other))
# check gaps
from datetime import date, timedelta
d0 = date(int(dates[0][:4]), int(dates[0][4:6]), int(dates[0][6:8]))
d1 = date(int(dates[-1][:4]), int(dates[-1][4:6]), int(dates[-1][6:8]))
n_days = (d1-d0).days + 1
print("calendar span days:", n_days, "files:", len(dates), "gaps:", n_days - len(dates))
