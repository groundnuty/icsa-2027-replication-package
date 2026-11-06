
import re, collections
files = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
print(len(files))
other=[f for f in files if not re.search(r'sst_\d{8}\.nc$',f)]
print(other[:20])
dates=sorted(re.search(r'sst_(\d{8})\.nc',f).group(1) for f in files if re.search(r'sst_\d{8}\.nc$',f))
print(dates[0],dates[-1],len(dates), len(set(dates)))
import datetime as dt
d0=dt.date(1991,12,27); d1=dt.date(2010,8,31)
exp={ (d0+dt.timedelta(i)).strftime('%Y%m%d') for i in range((d1-d0).days+1)}
print(len(exp), sorted(exp-set(dates))[:20], len(exp-set(dates)))
