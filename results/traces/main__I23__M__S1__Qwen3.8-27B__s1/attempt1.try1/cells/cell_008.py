import datetime as dt, json
def rng(a,b):
    t=a
    out=[]
    while t<=b:
        out.append(t)
        t+=dt.timedelta(days=1)
    return out
ext = rng(dt.date(1991,12,27), dt.date(2003,1,5))
print(len(ext), ext[0], ext[-1])
# consecutive?
ok = all((ext[i+1]-ext[i]).days==1 for i in range(len(ext)-1))
print("consecutive:", ok)
# count per year
from collections import Counter
c = Counter(d.year for d in ext)
print(sorted(c.items()))
# sanity: 1992-01-01 index, 2002-12-31 index
print("idx 1992-01-01:", ext.index(dt.date(1992,1,1)))
print("idx 2002-12-31:", ext.index(dt.date(2002,12,31)))
