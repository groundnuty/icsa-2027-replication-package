import os, re, datetime as dt
d = '/data/icsa2027_data_20261101T090944Z/s1z'
pat = re.compile(r'^sst_(\d{8})\.nc$')
have = {}
for f in os.listdir(d):
    m = pat.match(f)
    if m:
        s = m.group(1)
        have[dt.date(int(s[:4]), int(s[4:6]), int(s[6:8]))] = f
print('total parsed', len(have))
need = []
cur = dt.date(1991,12,27)
while cur <= dt.date(2004,8,31):
    need.append(cur)
    cur += dt.timedelta(days=1)
missing = [c for c in need if c not in have]
print('needed', len(need), 'missing', len(missing), missing[:10])
from collections import Counter
cnt = Counter(c.year for c in have if dt.date(1991,12,27) <= c <= dt.date(2004,8,31))
print({y: cnt[y] for y in sorted(cnt)})
