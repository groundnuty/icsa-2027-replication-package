import numpy as np, datetime as dt, pickle, time, warnings

data = np.load('/work/data_region.npy')          # (4632,60,60) float64, dates 1991-12-27..2004-08-31
with open('/work/all_dates.pkl','rb') as fh: dates = pickle.load(fh)
d0 = dates[0]
N = len(dates)

# ---- day-of-year mapping: fixed month/day table, leap-style (Mar 1 = 61 always, Dec 31 = 366)
CUM_LEAP = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
def doy_of(d):  # d: datetime.date
    return int(CUM_LEAP[d.month-1] + d.day)
# sanity
assert doy_of(dt.date(2001,1,1))==1 and doy_of(dt.date(2001,2,28))==59
assert doy_of(dt.date(2004,2,29))==60 and doy_of(dt.date(2004,3,1))==61
assert doy_of(dt.date(1993,3,1))==61 and doy_of(dt.date(1993,12,31))==365  # non-leap: no day 60, Dec31=365
assert doy_of(dt.date(2004,6,1))==153 and doy_of(dt.date(2004,8,31))==244
print('doy mapping OK')

# ---- baseline slice 1992-01-01..2002-12-31
bi0 = (dt.date(1992,1,1)-d0).days; bi1 = (dt.date(2002,12,31)-d0).days
bidx = np.arange(bi0, bi1+1)
bdates = [dates[i] for i in bidx]
bdoy = np.array([doy_of(d) for d in bdates])
print('baseline days:', len(bidx), bdates[0], bdates[-1])

# ---- pools: for doy d != 60, every date within +-5 calendar days of a baseline date with doy d
pool_idx = [None]*367
for d in range(1,367):
    if d==60: continue
    idxs=[]
    for i in range(len(bidx)):
        if bdoy[i]!=d: continue
        bd = bdates[i]
        for o in range(-5,6):
            j = (bd + dt.timedelta(days=o) - d0).days
            if 0 <= j < N:
                idxs.append(j)
    pool_idx[d] = np.array(sorted(set(idxs)), dtype=np.int64)

sizes = np.array([len(pool_idx[d]) if pool_idx[d] is not None else 0 for d in range(367)])
print('pool size stats: min', sizes[1:].min(), 'max', sizes[1:].max(), '(day60:', sizes[60], ')')
uniq, cnts = np.unique(sizes[1:], return_counts=True)
print('unique sizes:', uniq.tolist(), 'counts:', cnts.tolist())
# where do pools differ from 121?
odd = np.where(sizes!=121)[0]; odd = odd[odd!=60]
print('doys with size != 121:', odd.tolist())
print('pool day1 first/last global idx -> dates:', pool_idx[1][0], pool_idx[1][-1], dates[pool_idx[1][0]], dates[pool_idx[1][-1]])
print('pool day366 first/last -> dates:', dates[pool_idx[366][0]], dates[pool_idx[366][-1]])
print('pool day59 has Feb29 values:', sum(1 for j in pool_idx[59] if dates[j]==dt.date(1992,2,29) or dates[j]==dt.date(1996,2,29) or dates[j]==dt.date(2000,2,29)), 'extra leap-day entries')
print('pool day61 leap-day entries:', sum(1 for j in pool_idx[61] if dates[j].month==2 and dates[j].day==29))
np.save('/work/pool_sizes.npy', sizes)
with open('/work/pool_idx.pkl','wb') as fh: pickle.dump(pool_idx, fh)
print('pools built.')
