import numpy as np, datetime as dt, calendar, json
from itertools import groupby

S64 = np.load('/tmp/mhw/S32.npy').astype(np.float64)
dates = [dt.date.fromisoformat(str(s)) for s in np.load('/tmp/mhw/dates.npy')]
n_base_ext = 4028
thr_sm = np.load('/tmp/mhw/thr_sm.npy')
mask = np.load('/tmp/mhw/mask.npy')   # (92,60,60)
tgt_dates = dates[n_base_ext:]

def mapped_doy(d):
    if d.month==2 and d.day==29: return 60
    yday = d.timetuple().tm_yday
    return yday if calendar.isleap(d.year) else (yday if yday<=59 else yday+1)

tgt = S64[n_base_ext:]
finite_all = np.isfinite(tgt).all(axis=0)
doys = np.array([mapped_doy(d) for d in tgt_dates])

# independent reimplementation for sampled cells
rng = np.random.default_rng(7)
sea_cells = np.argwhere(finite_all)
sample = sea_cells[rng.choice(len(sea_cells), 250, replace=False)]
mism = 0
for (ii,jj) in sample:
    sst = tgt[:,ii,jj]
    hotd = np.array([sst[k] >= thr_sm[doys[k]-1, ii*60+jj] for k in range(92)])
    # runs via groupby
    runs=[]
    pos=0
    for val, grp in groupby(hotd):
        L=len(list(grp))
        if val: runs.append((pos,pos+L-1))
        pos+=L
    runs5=[(a,b) for a,b in runs if b-a+1>=5]
    merged=[]
    if runs5:
        cs,ce=runs5[0]
        for a,b in runs5[1:]:
            if a-ce-1<=2: ce=b
            else: merged.append((cs,ce)); cs,ce=a,b
        merged.append((cs,ce))
    ref = np.zeros(92, dtype=bool)
    for a,b in merged: ref[a:b+1]=True
    if not np.array_equal(ref, mask[:,ii,jj].astype(bool)):
        mism += 1
        print('MISMATCH', ii, jj, merged)
print('sampled 250 cells, mismatches:', mism)

# event structure: cells in MHW per day
ev_sum = mask.sum(axis=(1,2))
active_days = np.flatnonzero(ev_sum>0)
print('active days:', [str(tgt_dates[k]) for k in active_days[:5]], '...', [str(tgt_dates[k]) for k in active_days[-5:]])
print('cells in MHW per active day (min/max):', int(ev_sum[active_days].min()), int(ev_sum[active_days].max()))
import collections
print('active day counts by week:')
for k in active_days:
    pass
print(ev_sum[active_days])
# check non-active days all zero
print('non-active days all zero:', bool((ev_sum[ev_sum==0]==0).all()))
# any per-cell MHW crossing event boundaries? (should be impossible)
bnd = [active_days[0]-1, active_days[-1]+1]
print('mhw cells just before event start:', int(mask[bnd[0]].sum()) if bnd[0]>=0 else 'n/a',
      '| just after event end:', int(mask[bnd[1]].sum()) if bnd[1]<92 else 'n/a')
# distribution of per-cell MHW durations
durs=[]
for c in range(3600):
    col = mask[:,:,  ].reshape(92,-1)[:,c] if False else None
m = mask.reshape(92,-1)
for c in range(3600):
    col = m[:,c]
    if col.any():
        idx=np.flatnonzero(col)
        s=idx[0]; prev=idx[0]
        for k in idx[1:]:
            if k==prev+1: prev=k
            else: durs.append(prev-s+1); s=k; prev=k
        durs.append(prev-s+1)
durs=np.array(durs)
print('per-cell MHW count:', len(durs), 'duration min/median/max:', durs.min(), int(np.median(durs)), durs.max())
