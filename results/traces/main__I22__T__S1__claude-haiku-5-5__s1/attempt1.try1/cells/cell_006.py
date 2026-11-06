
import time, datetime as dt
D='icsa2027_data_20261101T090944Z/s1z'
start=dt.date(1991,12,27); end=dt.date(2004,8,31)
allds=[start+dt.timedelta(i) for i in range((end-start).days+1)]
t=time.time()
missing=[]
for d in allds:
    p=f"{D}/sst_{d:%Y%m%d}.nc"
    if not fs.exists(p): missing.append(d)
print('checked',len(allds),'missing',len(missing),missing[:20], time.time()-t)
