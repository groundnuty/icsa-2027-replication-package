import fsspec,datetime as dt,os
from concurrent.futures import ThreadPoolExecutor
fs=fsspec.filesystem('onedata')
P='icsa2027_data_20261101T090944Z/s1z/'
def days(a,b):
    d=a
    while d<=b: yield d; d+=dt.timedelta(1)
want=list(days(dt.date(1991,12,27),dt.date(2003,1,5)))+list(days(dt.date(2005,6,1),dt.date(2005,8,31)))
os.makedirs('/work/d',exist_ok=True)
def g(d):
    n=d.strftime('sst_%Y%m%d.nc');l='/work/d/'+n
    if os.path.exists(l):return None
    try: fs.get(P+n,l)
    except Exception as e: return (d,str(e)[:80])
with ThreadPoolExecutor(16) as t: r=[x for x in t.map(g,want) if x]
print(len(want),len(r),r[:10])