import datetime as dt, numpy as np
cum = [0,31,60,91,121,152,182,213,244,274,305,335]
mlen = [31,29,31,30,31,30,31,31,30,31,30,31]
def mdoy(y,m,d): return cum[m-1]+d
print('Jan1',mdoy(2007,1,1),'Feb28',mdoy(2007,2,28),'Feb29',mdoy(1996,2,29),
      'Mar1',mdoy(2007,3,1),'Jun1',mdoy(2007,6,1),'Aug31',mdoy(2007,8,31),'Dec31',mdoy(2007,12,31))
def build(y0,m0,d0,y1,m1,d1):
    a=dt.date(y0,m0,d0); b=dt.date(y1,m1,d1)
    return [a+dt.timedelta(days=i) for i in range((b-a).days+1)]
tgt = build(2007,6,1,2007,8,31)
print('target doy range:', mdoy(2007,tgt[0].month,tgt[0].day), mdoy(2007,tgt[-1].month,tgt[-1].day))
def inv(doy):
    for m in range(1,13):
        if 1 <= doy-cum[m-1] <= mlen[m-1]:
            return m, doy-cum[m-1]
assert all(inv(d) for d in range(1,367))
print('inv(60) =', inv(60), 'inv(366) =', inv(366), 'inv(153) =', inv(153), 'inv(244) =', inv(244))
ext = build(1991,12,27,2003,1,5)
orid = np.array([d.toordinal() for d in ext])
print('ext len', len(ext), ext[0], ext[-1])
sizes = {}
allused = np.zeros(len(ext),bool)
for doy in range(1,367):
    if doy==60: continue
    m,d = inv(doy)
    anchors = np.array([dt.date(Y,m,d).toordinal() for Y in range(1992,2003)])
    dist = np.min(np.abs(orid[:,None]-anchors[None,:]),axis=1)
    sel = dist<=5
    sizes[doy]=int(sel.sum())
    allused |= sel
import collections
print('pool size counter:', collections.Counter(sizes.values()))
print('size d=1,59,61,152,153,154,243,244,365,366:',
      sizes[1], sizes[59], sizes[61], sizes[152], sizes[153], sizes[154], sizes[243], sizes[244], sizes[365], sizes[366])
print('ext dates used:', int(allused.sum()), 'of', len(ext), ' unused:', int((~allused).sum()))
