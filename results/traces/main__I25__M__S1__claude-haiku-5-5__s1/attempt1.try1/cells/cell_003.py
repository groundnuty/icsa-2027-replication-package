import os
fs=sorted(os.listdir(d)); print(fs[0],fs[-1],len(fs)); print([f for f in fs if not f.startswith('sst_')][:10])
import re
dates=[f[4:12] for f in fs if re.match(r'sst_\d{8}\.nc$',f)]
print(len(dates), dates[0], dates[-1])
need=[x for x in dates if '19911227'<=x<='19930105' or '19920101'<=x<='20021231' or '20160601'<=x<='20160831']
print(len(need))
# check contiguity
import datetime as dt
s=set(dates); exp=[(dt.date(1991,12,27)+dt.timedelta(i)).strftime('%Y%m%d') for i in range((dt.date(2016,8,31)-dt.date(1991,12,27)).days+1)]
print(sum(e not in s for e in exp), [e for e in exp if e not in s][:20])