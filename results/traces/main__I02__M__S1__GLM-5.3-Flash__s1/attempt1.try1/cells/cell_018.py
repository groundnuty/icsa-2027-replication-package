import numpy as np, datetime as dt

tdata = np.load('/tmp/target.npy').astype(np.float64)   # (92,60,60)
tdate0 = dt.date(2004,6,1)
tdates = [tdate0+dt.timedelta(days=i) for i in range(tdata.shape[0])]

def doy_of(d):
    doy = (d - dt.date(d.year,1,1)).days + 1
    leap = (d.year%4==0 and (d.year%100!=0 or d.year%400==0))
    if not leap and doy >= 60: doy += 1
    return doy

tdoy = np.array([doy_of(d) for d in tdates])
print("target doys:", tdoy[0], "...", tdoy[-1])

thr_sm = np.load('/tmp/thr_sm.npy')      # (366,60,60)
sea = np.isfinite(tdata).all(axis=0)
print("sea cells:", sea.sum())

thr_t = thr_sm[tdoy-1]                   # (92,60,60)
hot = tdata >= thr_t                     # comparisons in float64
hot = hot & sea[None,:,:]                # land cells not hot

# per-cell runs and joining
T = tdata.shape[0]
mhw = np.zeros_like(hot, dtype=bool)
n_events_cells = 0
n_joined = 0
raw_seed_lens = []
for i in range(60):
    for j in range(60):
        if not sea[i,j]:
            continue
        h = hot[:,i,j]
        idx = np.flatnonzero(h)
        if idx.size==0: continue
        breaks = np.flatnonzero(np.diff(idx)>1)
        starts = np.concatenate(([idx[0]], idx[breaks+1]))
        ends   = np.concatenate((idx[breaks], [idx[-1]]))
        seeds = [(int(s),int(e)) for s,e in zip(starts,ends) if e-s+1>=5]
        raw_seed_lens += [e-s+1 for s,e in seeds]
        if not seeds: continue
        # join seeds separated by <=2 non-hot days
        merged=[list(seeds[0])]
        for s,e in seeds[1:]:
            if s - merged[-1][1] - 1 <= 2:
                merged[-1][1]=e
                n_joined+=1
            else:
                merged.append([s,e])
        for s,e in merged:
            mhw[s:e+1,i,j]=True
            n_events_cells+=1

print("per-cell MHW segments (after joining):", n_events_cells, " joins performed:", n_joined)
import collections
print("raw seed length distribution:", dict(sorted(collections.Counter(raw_seed_lens).items())))

active = mhw.any(axis=(1,2))
print("active days:", active.sum(), "of", T)
# regional events: maximal runs of consecutive active days
idx=np.flatnonzero(active)
ev=[]
if idx.size:
    br=np.flatnonzero(np.diff(idx)>1)
    st=np.concatenate(([idx[0]], idx[br+1])); en=np.concatenate((idx[br],[idx[-1]]))
    ev=[(int(s),int(e)) for s,e in zip(st,en)]
print("regional events:", ev)
for s,e in ev:
    print(f"  {tdates[s]} .. {tdates[e]}  ({e-s+1} days)")

np.save('/tmp/mhw.npy', mhw)
np.save('/tmp/active.npy', active)
