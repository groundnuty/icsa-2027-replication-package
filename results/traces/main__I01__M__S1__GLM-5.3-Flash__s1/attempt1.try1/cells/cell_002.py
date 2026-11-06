import os
files = sorted(os.listdir('/data/icsa2027_data_20261101T090944Z/s1z'))
print(len(files), files[0], files[-1])
# check for gaps in date sequence
import datetime as dt
dates = [dt.datetime.strptime(f[4:12], '%Y%m%d').date() for f in files]
print(dates[0], dates[-1])
missing = []
d = dates[0]
i = 0
while d <= dates[-1]:
    if i < len(dates) and dates[i] == d:
        i += 1
    else:
        missing.append(str(d))
    d += dt.timedelta(days=1)
print('missing count:', len(missing), missing[:20])
