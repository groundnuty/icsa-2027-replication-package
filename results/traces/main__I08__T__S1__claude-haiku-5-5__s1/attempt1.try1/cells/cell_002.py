import re,collections
files = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
names=[f.split('/')[-1] for f in files]
print(len(names))
pat=re.compile(r'^sst_(\d{8})\.nc$')
odd=[n for n in names if not pat.match(n)]
print(len(odd), odd[:20])
dates=sorted(pat.match(n).group(1) for n in names if pat.match(n))
print(dates[0], dates[-1], len(dates))
import datetime
d0=datetime.date(1991,12,27); 
exp=[]
d=datetime.date(1991,12,27)
while d<=datetime.date(2003,1,5):
    exp.append(d.strftime('%Y%m%d')); d+=datetime.timedelta(1)
print(len(exp), len(set(exp)-set(dates)), sorted(set(exp)-set(dates))[:10])