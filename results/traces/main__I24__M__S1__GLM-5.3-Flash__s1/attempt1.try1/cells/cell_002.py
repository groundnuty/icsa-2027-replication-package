import os
d = '/data/icsa2027_data_20261101T090944Z/s1z'
files = sorted(os.listdir(d))
print(len(files))
print(files[0], files[-1])
# check contiguity of dates
import datetime as dt
dates = [dt.datetime.strptime(f[4:12], '%Y%m%d').date() for f in files]
print(dates[0], dates[-1])
gaps = [(dates[i-1], dates[i]) for i in range(1, len(dates)) if (dates[i]-dates[i-1]).days != 1]
print('num gaps:', len(gaps))
print(gaps[:10])
