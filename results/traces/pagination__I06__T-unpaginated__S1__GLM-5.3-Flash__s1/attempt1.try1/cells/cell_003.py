import fsspec, re, os
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
items = fs.ls(base, detail=True)
dates = []
other = []
for it in items:
    n = os.path.basename(it['name'])
    m = re.match(r'sst_(\d{8})\.nc$', n)
    if m: dates.append(m.group(1))
    else: other.append(n)
dates.sort()
print("n date files:", len(dates))
print("first:", dates[:3], "last:", dates[-3:])
print("other:", other[:20], len(other))
import datetime as dt
def daterange(a,b):
    d0=dt.date(*map(int,[a[:4],a[4:6],a[6:]])); d1=dt.date(*map(int,[b[:4],b[4:6],b[6:]]))
    out=[]; d=d0
    while d<=d1:
        out.append(d.strftime("%Y%m%d")); d+=dt.timedelta(days=1)
    return out
have=set(dates)
for y0,y1 in [(1991,1991),(1992,2002),(2003,2003),(2012,2012)]:
    rng = daterange(f"{y0}0101", f"{y1}1231")
    miss = [d for d in rng if d not in have]
    print(f"{y0}-{y1}: expected {len(rng)}, missing {len(miss)}", miss[:10])
missing_all = [d for d in daterange(dates[0], dates[-1]) if d not in have]
print("total missing across full range:", len(missing_all), missing_all[:20])
