import fsspec
fs = fsspec.filesystem('onedata')
base='/icsa2027_data_20261101T090944Z/s1z'
names=[n.split('/')[-1] for n in fs.ls(base)]
print('n files:', len(names))
print('first:', names[0], 'last:', names[-1])
# parse dates
import re
dstr=sorted(n[4:12] for n in names if n.startswith('sst_') and n.endswith('.nc'))
print('n dated:', len(dstr))
print('min', dstr[0], 'max', dstr[-1])
# check contiguity
import datetime as dt
dates=[dt.datetime.strptime(d,'%Y%m%d').date() for d in dstr]
full=set(dt.date(1981,1,1)+dt.timedelta(days=i) for i in range((dates[-1]-dates[0]).days+1))
missing=sorted(full-set(dates))
extra=set(dates)-full
print('missing count:', len(missing))
print('missing sample:', [m.isoformat() for m in missing[:20]])
print('missing around 1992-2003:', [m.isoformat() for m in missing if dt.date(1991,1,1)<=m<=dt.date(2003,12,31)][:20])
print('missing in 2009:', [m.isoformat() for m in missing if m.year==2009][:20])
print('extra:', sorted(x.isoformat() for x in extra)[:10])
