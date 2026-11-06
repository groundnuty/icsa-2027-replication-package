import fsspec, collections
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# Try find (recursive listing)
try:
    allf = fs.find(base)
    print('find returned', len(allf))
except Exception as e:
    print('find ERR', repr(e))
    allf = []

years = collections.Counter()
dates = set()
for p in allf:
    name = p.rsplit('/',1)[-1]
    if name.startswith('sst_') and name.endswith('.nc'):
        d = name[4:12]
        if len(d)==8 and d.isdigit():
            dates.add(d)
            years[d[:4]] += 1
print('total parsed:', len(dates))
print('years:', dict(sorted(years.items())))
ds_ = sorted(dates)
print('first:', ds_[:3], 'last:', ds_[-3:])
# check leap days present
print('20040229 present:', '20040229' in dates, '19960229:', '19960229' in dates, '20000229:', '20000229' in dates)
# check continuity
import datetime as dt
d0 = dt.date(*map(int, ds_[0][:4]+[ds_[0][4:6], ds_[0][6:8]])) if False else None
d0 = dt.date(int(ds_[0][:4]), int(ds_[0][4:6]), int(ds_[0][6:8]))
d1 = dt.date(int(ds_[-1][:4]), int(ds_[-1][4:6]), int(ds_[-1][6:8]))
all_days = []
d = d0
while d <= d1:
    all_days.append(d.strftime('%Y%m%d'))
    d += dt.timedelta(days=1)
missing = sorted(set(all_days) - dates)
print('n missing days in range:', len(missing), missing[:10], missing[-10:] if missing else '')
