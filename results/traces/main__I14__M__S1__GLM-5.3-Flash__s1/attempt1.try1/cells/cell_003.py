import os, datetime as dt
d = "/data/icsa2027_data_20261101T090944Z/s1z"

# Check availability of all needed dates: extension + baseline + target
start = dt.date(1991,12,27); end = dt.date(2003,1,5)
missing = []
n = 0
cur = start
while cur <= end:
    f = os.path.join(d, f"sst_{cur:%Y%m%d}.nc")
    if not os.path.exists(f): missing.append(str(cur))
    n += 1
    cur += dt.timedelta(days=1)
print("baseline+ext range:", start, end, "days:", n, "missing:", len(missing), missing[:10])

t0 = dt.date(2015,6,1); t1 = dt.date(2015,8,31)
missing_t = []
cur = t0
while cur <= t1:
    f = os.path.join(d, f"sst_{cur:%Y%m%d}.nc")
    if not os.path.exists(f): missing_t.append(str(cur))
    cur += dt.timedelta(days=1)
print("target missing:", len(missing_t), missing_t[:10])

# full extent of dataset
files = sorted(os.listdir(d))
print("first file:", files[0], "last file:", files[-1], "count:", len(files))
