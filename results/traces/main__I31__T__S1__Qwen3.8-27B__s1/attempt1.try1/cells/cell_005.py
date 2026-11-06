
import fsspec, re, collections, datetime
fs = fsspec.filesystem('onedata')
entries = fs.ls('/icsa2027_data_20261101T090944Z/s2z', detail=True)
print("num entries:", len(entries))
for e in entries[:3]:
    print(e)
pat = re.compile(r'sst_(\d{8})\.nc$')
years = collections.Counter()
nonmatch = []
dates = []
for e in entries:
    name = e['name'].split('/')[-1]
    m = pat.match(name)
    if m:
        dates.append(int(m.group(1)))
        years[m.group(1)[:4]] += 1
    else:
        nonmatch.append(name)
print("years:", dict(sorted(years.items())))
print("non-matching:", nonmatch[:10], "count:", len(nonmatch))
dates.sort()
print("first:", dates[0], "last:", dates[-1])
all_dates = [datetime.date(d//10000,(d//100)%100,d%100) for d in dates]
missing = []
d = all_dates[0]; end = all_dates[-1]
s = set(all_dates)
while d <= end:
    if d not in s: missing.append(d)
    d += datetime.timedelta(days=1)
print("missing:", len(missing), missing[:10])
