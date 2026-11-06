import os
files = sorted(os.listdir('/data/icsa2027_data_20261101T090944Z/s1z'))
print(len(files), files[0], files[-1])
# verify all names parse and dates contiguous
import datetime as dt
dates = [dt.datetime.strptime(f[4:12], '%Y%m%d').date() for f in files]
print(dates[0], dates[-1])
missing = []
d = dates[0]
while d <= dates[-1]:
    if d not in dates:
        missing.append(d)
    d += dt.timedelta(days=1)
print('missing count:', len(missing), missing[:10])
# check leap years present
years = sorted(set(x.year for x in dates))
print(years[:5], years[-5:], len(years))
