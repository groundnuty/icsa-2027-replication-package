import numpy as np, datetime as dt

thr_raw=np.load('/tmp/thr_raw.npy'); clim_raw=np.load('/tmp/clim_raw.npy')
# circular 31-day moving mean, wrap mod 366; day d (1..366) = mean of raw[d-15..d+15] mod 366
idx=np.arange(366)
win=(idx[:,None]+np.arange(-15,16)[None,:])%366   # (366,31) row i -> days i-15..i+15 mod 366
def circ31(x):
    return x[win,:].mean(axis=1)
thr=circ31(thr_raw)
clim=circ31(clim_raw)
print('thr NaNs after smooth:',int(np.isnan(thr).sum()),'clim NaNs:',int(np.isnan(clim).sum()))
np.save('/tmp/thr.npy',thr); np.save('/tmp/clim.npy',clim)

A=np.load('/tmp/A_all.npy'); ords=np.load('/tmp/dates_ord.npy')
dates=[dt.date.fromordinal(int(o)) for o in ords]
def doy_map(d):
    y=d.timetuple().tm_yday
    leap = d.year%4==0 and (d.year%100!=0 or d.year%400==0)
    return y if leap else (y+1 if y>=60 else y)
doy=np.array([doy_map(d) for d in dates])
ti=4540; tj=4631   # target indices (checked earlier: 2004-06-01..2004-08-31)
# hot: SST >= smoothed threshold (NaN comparisons -> False)
hot = A[ti:tj+1] >= thr[doy[ti:tj+1],None,:]     # (92,60,60) bool
print('hot days total (incl land False):',int(hot.sum()))
# per-cell MHW: runs>=5 joined over gaps<=2, restricted to target window
T=hot.shape[0]
inmhw=np.zeros_like(hot)
for i in range(60):
    for j in range(60):
        h=hot[:,i,j]
        if not h.any(): continue
        # find runs
        d=np.diff(np.concatenate(([0],h.view(np.int8),[0])))
        starts=np.where(d==1)[0]; ends=np.where(d==-1)[0]-1
        runs=[(s,e) for s,e in zip(starts,ends) if e-s+1>=5]
        # join runs with gaps <=2
        if not runs: continue
        merged=[list(runs[0])]
        for s,e in runs[1:]:
            if s - merged[-1][1] - 1 <= 2:
                merged[-1][1]=e
            else:
                merged.append([s,e])
        for s,e in merged:
            inmhw[s:e+1,i,j]=True
print('in-mhw cell-days:',int(inmhw.sum()))
# active days: any cell in mhw
active=inmhw.any(axis=(1,2))
print('active days:',int(active.sum()),'of',T)
# regional events: maximal runs of active days
d2=np.diff(np.concatenate(([0],active.view(np.int8),[0])))
starts=np.where(d2==1)[0]; ends=np.where(d2==-1)[0]-1
ev=[(dates[ti+s],dates[ti+e]) for s,e in zip(starts,ends)]
print('events:',len(ev))
for s,e in ev: print('  ',s,'->',e,'(%d days)'%((e-s).days+1))
np.save('/tmp/inmhw.npy',inmhw)
import json
json.dump([[s.isoformat(),e.isoformat()] for s,e in ev],open('/tmp/events.json','w'))
