from concurrent.futures import ThreadPoolExecutor
def days(a,b):
    d=a
    while d<=b: yield d; d+=dt.timedelta(1)
want=list(days(dt.date(1991,12,27),dt.date(2003,1,5)))+list(days(dt.date(2005,6,1),dt.date(2005,8,31)))
def ex(d): return fs.exists(P+d.strftime('sst_%Y%m%d.nc'))
with ThreadPoolExecutor(16) as t: r=list(t.map(ex,want))
miss=[d for d,e in zip(want,r) if not e];print(len(want),miss[:20],len(miss))