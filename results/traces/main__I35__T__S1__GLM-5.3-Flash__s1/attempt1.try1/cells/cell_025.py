import numpy as np, datetime as dt, calendar
# Rebuild pool indices correctly:
# pool(d) = union over baseline dates B with doy(B)=d of {SST(date): date in [B-5, B+5]}
z=np.load('/work/extracted.npz', allow_pickle=False)
EXT=[dt.date.fromisoformat(s) for s in z['ext_dates']]
def doy_of(d):
    y=d.timetuple().tm_yday
    if calendar.isleap(d.year): return y
    return y+1 if y>=60 else y
ext_doy0=np.array([doy_of(d)-1 for d in EXT])
# map: doy0 -> list of EXT indices of BASELINE dates (1992-01-01..2002-12-31) with that doy
from collections import defaultdict
base=defaultdict(list)
for i,d in enumerate(EXT):
    if dt.date(1992,1,1)<=d<=dt.date(2002,12,31):
        base[ext_doy0[i]].append(i)
print('doy0 59 (Feb29) baseline dates:', [EXT[i].isoformat() for i in base[59]])
print('doy0 0 (Jan1) baseline dates:', len(base[0]), 'years', [EXT[i].year for i in base[0]])
# build pool index array
idx=np.full((366,121), -1, dtype=np.int32)
for d0 in range(366):
    if d0==59: continue
    bs=base[d0]
    assert len(bs)==11, (d0, len(bs))
    k=0
    for ib in bs:
        assert ib-5>=0 and ib+5<len(EXT), (d0, ib)
        for j in range(ib-5, ib+6):
            idx[d0,k]=j; k+=1
    assert k==121
print('pool idx built. all >=0:', bool((idx>=0).all()))
# sanity: pool of d0=0 (Jan 1) should include 1991-12-27..31 (indices 0..4) and 1992-01-01..06 etc.
print('pool(Jan1) first 16 dates:', [EXT[i].isoformat() for i in idx[0,:16]])
print('pool(Jan1) last 6 dates:', [EXT[i].isoformat() for i in idx[0,-6:]])
# no duplicates within a pool? (windows of same doy in different years are disjoint)
dupes=[d0 for d0 in range(366) if d0!=59 and len(np.unique(idx[d0]))!=121]
print('doys with duplicate pool dates:', dupes)
# date ranges per pool: min and max date index
print('pool(Dec31=365) dates:', [EXT[i].isoformat() for i in idx[365,:11]], '...', [EXT[i].isoformat() for i in idx[365,-6:]])
np.save('/work/pool_idx.npy', idx)
