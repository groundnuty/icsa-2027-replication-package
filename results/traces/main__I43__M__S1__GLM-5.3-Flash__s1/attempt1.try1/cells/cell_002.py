import os, re
files = sorted(os.listdir('/data/icsa2027_data_20261101T090944Z/s1z'))
print(len(files), files[0], files[-1])
# check all match pattern
pat = re.compile(r'^sst_(\d{8})\.nc$')
dates = []
for f in files:
    m = pat.match(f)
    if not m:
        print('non-matching:', f)
    else:
        dates.append(m.group(1))
print(len(dates), dates[0], dates[-1])
# check continuity
from datetime import date, timedelta
d0 = date(int(dates[0][:4]), int(dates[0][4:6]), int(dates[0][6:]))
d1 = date(int(dates[-1][:4]), int(dates[-1][4:6]), int(dates[-1][6:]))
expect = (d1 - d0).days + 1
print('expected days:', expect, 'actual:', len(dates))
s = set(dates)
missing = []
cur = d0
while cur <= d1:
    if cur.strftime('%Y%m%d') not in s:
        missing.append(cur.isoformat())
    cur += timedelta(days=1)
print('missing:', missing[:50], 'count', len(missing))
