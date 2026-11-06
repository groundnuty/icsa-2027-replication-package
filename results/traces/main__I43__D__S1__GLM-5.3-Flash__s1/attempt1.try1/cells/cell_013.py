import fsspec, time, os, datetime as dt, json
fs = fsspec.filesystem('onedata')
p = 'icsa2027_data_20261101T090944Z/s1z'

# Build full date list: baseline window (1991-12-27 .. 2003-01-05) + target (2017-06-01..2017-08-31)
dates = []
d = dt.date(1991,12,27)
while d <= dt.date(2003,1,5):
    dates.append(d); d += dt.timedelta(days=1)
target_dates = []
d = dt.date(2017,6,1)
while d <= dt.date(2017,8,31):
    target_dates.append(d); d += dt.timedelta(days=1)
alldates = dates + target_dates
print('baseline-window days', len(dates), 'target days', len(target_dates), 'total', len(alldates))

t0=time.time()
missing = []
for d in alldates:
    name = f'sst_{d:%Y%m%d}.nc'
    try:
        fs.info(p + '/' + name)
    except Exception:
        missing.append(name)
t1=time.time()
print('existence check done in', round(t1-t0,1), 's; missing:', len(missing))
print(missing[:20])
with open('/work/dates.json','w') as f:
    json.dump({'baseline_window':[str(x) for x in dates], 'target':[str(x) for x in target_dates], 'missing':missing}, f)
