import datetime as dt, numpy as np
# Spec DOY mapping: fixed 366-day calendar by (month, day)
cum = [0,31,60,91,121,152,183,213,244,275,306,336]  # cum days before month m (Feb=29)
mlen = [31,29,31,30,31,30,31,31,30,31,30,31]
def mdoy(y,m,d): return cum[m-1]+d
# checks
print('Jan1',mdoy(2007,1,1),'Feb28',mdoy(2007,2,28),'Feb29',mdoy(1996,2,29),
      'Mar1',mdoy(2007,3,1),'Jun1',mdoy(2007,6,1),'Aug31',mdoy(2007,8,31),'Dec31',mdoy(2007,12,31))
# target doys
def build(y0,m0,d0,y1,m1,d1):
    a=dt.date(y0,m0,d0); b=dt.date(y1,m1,d1)
    return [a+dt.timedelta(days=i) for i in range((b-a).days+1)]
tgt = build(2007,6,1,2007,8,31)
print('target doy range:', mdoy(2007,tgt[0].month,tgt[0].day), mdoy(2007,tgt[-1].month,tgt[-1].day))
# inverse mapping
def inv(doy):
    for m in range(1,13):
        if 1 <= doy-cum[m-1] <= mlen[m-1]:
            return m, doy-cum[m-1]
    return None
assert all(inv(d) is not None for d in range(1,367))
print('inv(60) =', inv(60), 'inv(366) =', inv(366), 'inv(153) =', inv(153))

# ext range dates and ordinals
ext = build(1991,12,27,2003,1,5)
orid = np.array([d.toordinal() for d in ext])
print('ext len', len(ext), ext[0], ext[-1])
# pool masks per doy (calendar-day windows around baseline dates with same (month,day))
sizes = {}
for doy in range(1,367):
    if doy==60: continue
    m,d = inv(doy)
    anchors = [dt.date(Y,m,d).toordinal() for Y in range(1992,2003)]
    dist = np.min(np.abs(orid[:,None]-np.array(anchors)[None,:]),axis=1)
    sel = dist<=5
    sizes[doy]=int(sel.sum())
import collections
print('pool size counter:', collections.Counter(sizes.values()))
print('size d=1,59,61,365,366:', sizes[1], sizes[59], sizes[61], sizes[365], sizes[366])
# every ext date used in >=1 pool?
allused = np.zeros(len(ext),bool)
for doy in range(1,367):
    if doy==60: continue
    m,d = inv(doy)
    anchors = np.array([dt.date(Y,m,d).toordinal() for Y in range(1992,2003)])
    allused |= (np.min(np.abs(orid[:,None]-anchors[None,:]),axis=1)<=5)
print('ext dates used:', int(allused.sum()), 'of', len(ext))
# which ext dates are never used (should be none)
print('unused:', [str(ext[i]) for i in np.where(~allused)[0][:10]])
