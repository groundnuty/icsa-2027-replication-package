
import fsspec, re, json
fs = fsspec.filesystem('onedata')
names = [p.split('/')[-1] for p in fs.ls('/icsa2027_data_20261101T090944Z/s1z')]
pat = re.compile(r'sst_(\d{8})\.nc$')
dates = sorted(int(pat.match(n).group(1)) for n in names if pat.match(n))
print("n files:", len(dates))
print("first:", dates[0], "last:", dates[-1])
# check contiguity
import datetime
all_dates = [datetime.date(d//10000, (d//100)%100, d%100) for d in dates]
missing = []
cur = all_dates[0]
end = all_dates[-1]
d = cur
while d <= end:
    if d not in set(all_dates):
        missing.append(d)
    d += datetime.timedelta(days=1)
print("missing within range:", missing[:20], "count:", len(missing))
# what we need: 1991-12-27 .. 1992..2002-12-31, 2003-01-01..05, 2017-06-01..08-31
need = set()
import itertools
d = datetime.date(1991,12,27)
while d <= datetime.date(1992,1,5):
    need.add(d); d += datetime.timedelta(days=1)
d = datetime.date(1992,1,1)
while d <= datetime.date(2002,12,31):
    need.add(d); d += datetime.timedelta(days=1)
d = datetime.date(2003,1,1)
while d <= datetime.date(2003,1,5):
    need.add(d); d += datetime.timedelta(days=1)
d = datetime.date(2017,6,1)
while d <= datetime.date(2017,8,31):
    need.add(d); d += datetime.timedelta(days=1)
have = set(all_dates)
lack = sorted(x for x in need if x not in have)
print("needed days missing from dataset:", lack[:30], "count:", len(lack))
print("total needed:", len(need))
