import fsspec, re, datetime as dt
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
# Try glob for full listing (may bypass 1000-entry page limit)
paths = fs.glob(f'{base}/sst_*.nc')
print("glob count:", len(paths))
names = [p.rsplit('/',1)[-1] for p in paths]
print("first/last:", names[0], names[-1])
dates = sorted(dt.datetime.strptime(n[4:12], "%Y%m%d").date() for n in names)
print("date range:", dates[0], dates[-1])
print("unique:", len(set(dates)))
# missing days in baseline+target needs
need = set()
cur = dt.date(1991,12,26)
while cur <= dt.date(2003,1,6):
    need.add(cur); cur += dt.timedelta(days=1)
present = set(dates)
print("missing in 1991-12-26..2003-01-06:", sorted(need - present)[:20], len(need - present))
need2 = set()
cur = dt.date(2012,5,30)
while cur <= dt.date(2012,9,2):
    need2.add(cur); cur += dt.timedelta(days=1)
print("missing in 2012-05-30..2012-09-02:", sorted(need2 - present))
