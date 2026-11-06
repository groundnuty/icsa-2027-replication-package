import numpy as np, datetime as dt, pickle, json, os

data=np.load('/work/data_region.npy')
with open('/work/all_dates.pkl','rb') as fh: dates=pickle.load(fh)
z=np.load('/work/raw.npz')
thr_raw=np.full((367,60,60), np.nan); thr_raw[1:]=z['thr_raw']
clim_raw=np.full((367,60,60), np.nan); clim_raw[1:]=z['clim_raw']
d0=dates[0]

t_start=dt.date(2004,6,1); t_end=dt.date(2004,8,31)
ti0=(t_start-d0).days; ti1=(t_end-d0).days
target=data[ti0:ti1+1]                       # (92,60,60) float64 kelvin
sea=np.isfinite(target).all(axis=0)
print('sea cells:', int(sea.sum()))

CUM_LEAP=np.array([0,31,60,91,121,152,182,213,244,274,305,335])
def doy_of(d): return int(CUM_LEAP[d.month-1]+d.day)

def circ_smooth(a):
    trip=np.concatenate([a,a,a],axis=0); c=np.cumsum(trip,axis=0)
    out=np.empty_like(a)
    for k in range(366):
        out[k]=(c[k+366+15]-c[k+366-16])/31.0
    return out
thr=np.full((367,60,60), np.nan); thr[1:]=circ_smooth(thr_raw[1:])
clim=np.full((367,60,60), np.nan); clim[1:]=circ_smooth(clim_raw[1:])
print('smoothed sea finite:', bool(np.isfinite(thr[1:].reshape(366,-1)[:, sea.ravel()]).all()),
      bool(np.isfinite(clim[1:].reshape(366,-1)[:, sea.ravel()]).all()))

# hot days
hot=np.zeros(target.shape, dtype=bool)
for k in range(target.shape[0]):
    hot[k]=target[k]>=thr[doy_of(t_start+dt.timedelta(days=k))]
print('hot fraction over sea cells:', float(hot[:,sea].mean()))
hp=hot[:,sea].sum(axis=0)
print('hot days per sea cell: min', int(hp.min()), 'max', int(hp.max()), 'mean', float(hp.mean()))
print('cells with zero hot days:', int((hp==0).sum()))

# per-cell MHW: runs>=5, join gaps<=2 (calendar gap between consecutive kept runs)
def cell_mhw(h):
    m=np.zeros(h.size, dtype=bool)
    idx=np.flatnonzero(h)
    if idx.size==0: return m
    br=np.flatnonzero(np.diff(idx)>1)
    starts=np.r_[idx[0], idx[br+1]]; ends=np.r_[idx[br], idx[-1]]
    keep=(ends-starts+1)>=5
    if not keep.any(): return m
    s=starts[keep]; e=ends[keep]
    ms=[s[0]]; me=[e[0]]
    for k in range(1,len(s)):
        if s[k]-me[-1]-1<=2: me[-1]=e[k]
        else: ms.append(s[k]); me.append(e[k])
    for a,b in zip(ms,me): m[a:b+1]=True
    return m

mhw=np.zeros(hot.shape, dtype=bool)
t0=time.time()
for i in range(60):
    for j in range(60):
        if sea[i,j]:
            mhw[:,i,j]=cell_mhw(hot[:,i,j])
print('cell loop seconds:', time.time()-t0)
mp=mhw[:,sea].sum(axis=0)
print('cells with >=1 MHW day:', int((mp>0).sum()), '/', int(sea.sum()))
print('MHW days per cell: min', int(mp.min()), 'max', int(mp.max()), 'mean', float(mp.mean()))
print('total MHW cell-days:', int(mhw.sum()))

# regional events
active=mhw.any(axis=(1,2)) | mhw[:,~sea].any(axis=(1,2))  # ~sea cells are all False anyway
act=active
idx=np.flatnonzero(act)
ev=[]
if idx.size:
    br=np.flatnonzero(np.diff(idx)>1)
    starts=np.r_[idx[0], idx[br+1]]; ends=np.r_[idx[br], idx[-1]]
    ev=[(starts[k],ends[k]) for k in range(len(starts))]
print('active days:', int(act.sum()), 'of', act.size)
events=[{'onset':str(t_start+dt.timedelta(days=int(a))),'end':str(t_start+dt.timedelta(days=int(b)))} for a,b in ev]
print('regional events:', events)

np.savez_compressed('/work/final.npz', sea=sea, hot=hot, mhw=mhw, active=act)
with open('/work/events.json','w') as fh: json.dump(events, fh)
print('saved final arrays.')
