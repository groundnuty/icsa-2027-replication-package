import numpy as np, datetime as dt

thr=np.load('/tmp/thr.npy'); clim=np.load('/tmp/clim.npy')
A=np.load('/tmp/A_all.npy'); ords=np.load('/tmp/dates_ord.npy')
dates=[dt.date.fromordinal(int(o)) for o in ords]
def doy_map(d):
    y=d.timetuple().tm_yday
    leap = d.year%4==0 and (d.year%100!=0 or d.year%400==0)
    return y if leap else (y+1 if y>=60 else y)
doy=np.array([doy_map(d) for d in dates])
ti=4540; tj=4631
thr3=thr.reshape(366,60,60)
# hot: SST >= smoothed threshold (NaN -> False)
hot = A[ti:tj+1] >= thr3[doy[ti:tj+1]]           # (92,60,60)
print('hot cell-days:',int(hot.sum()))
T=hot.shape[0]
inmhw=np.zeros_like(hot)
import time as _t
t0=_t.time()
for i in range(60):
    for j in range(60):
        h=hot[:,i,j]
        if not h.any(): continue
        d=np.diff(np.concatenate(([0],h.view(np.int8),[0])))
        starts=np.where(d==1)[0]; ends=np.where(d==-1)[0]-1
        runs=[(s,e) for s,e in zip(starts,ends) if e-s+1>=5]
        if not runs: continue
        merged=[list(runs[0])]
        for s,e in runs[1:]:
            if s - merged[-1][1] - 1 <= 2:
                merged[-1][1]=e
            else:
                merged.append([s,e])
        for s,e in merged:
            inmhw[s:e+1,i,j]=True
print('per-cell loop %.2fs'%(_t.time()-t0))
print('in-mhw cell-days:',int(inmhw.sum()))
active=inmhw.any(axis=(1,2))
print('active days:',int(active.sum()),'of',T)
d2=np.diff(np.concatenate(([0],active.view(np.int8),[0])))
starts=np.where(d2==1)[0]; ends=np.where(d2==-1)[0]-1
ev=[(dates[ti+s],dates[ti+e]) for s,e in zip(starts,ends)]
print('regional events:',len(ev))
for s,e in ev: print('  ',s,'->',e,'(%d days)'%((e-s).days+1))
np.save('/tmp/inmhw.npy',inmhw)
import json
json.dump([[s.isoformat(),e.isoformat()] for s,e in ev],open('/tmp/events.json','w'))
