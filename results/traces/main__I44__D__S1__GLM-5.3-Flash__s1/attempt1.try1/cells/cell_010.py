import numpy as np, datetime as dt, pickle

data = np.load('/work/data_region.npy')
with open('/work/all_dates.pkl','rb') as fh: dates = pickle.load(fh)
d0 = dates[0]; N=len(dates)

CUM_LEAP = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
def doy_of(d):
    return int(CUM_LEAP[d.month-1] + d.day)
assert doy_of(dt.date(2001,1,1))==1 and doy_of(dt.date(2001,2,28))==59
assert doy_of(dt.date(2004,2,29))==60 and doy_of(dt.date(2004,3,1))==61
assert doy_of(dt.date(1993,3,1))==61 and doy_of(dt.date(1993,12,31))==366
assert doy_of(dt.date(2001,12,31))==366 and doy_of(dt.date(1996,12,31))==366
assert doy_of(dt.date(2004,6,1))==153 and doy_of(dt.date(2004,8,31))==244
# no baseline date maps to 60 unless it is Feb 29
for d in dates:
    if d.month==2 and d.day==29: assert doy_of(d)==60
    else: assert doy_of(d)!=60
print('doy mapping OK for all 4632 dates')

bi0=(dt.date(1992,1,1)-d0).days; bi1=(dt.date(2002,12,31)-d0).days
bidx=np.arange(bi0,bi1+1)
bdates=[dates[i] for i in bidx]
bdoy=np.array([doy_of(d) for d in bdates])
print('baseline days:', len(bidx), bdates[0], bdates[-1])

pool_idx=[None]*367
for d in range(1,367):
    if d==60: continue
    idxs=[]
    for i in range(len(bidx)):
        if bdoy[i]!=d: continue
        bd=bdates[i]
        for o in range(-5,6):
            j=(bd+dt.timedelta(days=o)-d0).days
            if 0<=j<N: idxs.append(j)
    pool_idx[d]=np.array(sorted(set(idxs)),dtype=np.int64)

sizes=np.array([len(pool_idx[d]) if pool_idx[d] is not None else 0 for d in range(367)])
print('pool size min/max (excl 60):', sizes[1:].min(), sizes[1:].max(), '| day60:',sizes[60])
odd=np.where(sizes!=121)[0]; odd=odd[odd!=60]
print('doys with size != 121:', odd.tolist())
print('day1 pool dates:', dates[pool_idx[1][0]], '..', dates[pool_idx[1][-1]], 'n=',len(pool_idx[1]))
print('day366 pool dates:', dates[pool_idx[366][0]], '..', dates[pool_idx[366][-1]], 'n=',len(pool_idx[366]))
print('day59 includes Feb29 (92,96,00):', [str(dates[j]) for j in pool_idx[59] if dates[j].month==2 and dates[j].day==29])
print('day61 includes Feb29:', [str(dates[j]) for j in pool_idx[61] if dates[j].month==2 and dates[j].day==29])
with open('/work/pool_idx.pkl','wb') as fh: pickle.dump(pool_idx, fh)
print('pools built & saved')
