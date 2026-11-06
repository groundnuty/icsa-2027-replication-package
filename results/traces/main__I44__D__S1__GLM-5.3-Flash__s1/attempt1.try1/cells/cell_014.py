import numpy as np, datetime as dt, pickle, json, os, time

data=np.load('/work/data_region.npy')
with open('/work/all_dates.pkl','rb') as fh: dates=pickle.load(fh)
z=np.load('/work/raw.npz')
thr_raw=np.full((367,60,60), np.nan); thr_raw[1:]=z['thr_raw']
d0=dates[0]
t_start=dt.date(2004,6,1); t_end=dt.date(2004,8,31)
ti0=(t_start-d0).days; ti1=(t_end-d0).days
target=data[ti0:ti1+1]
sea=np.isfinite(target).all(axis=0)

CUM_LEAP=np.array([0,31,60,91,121,152,182,213,244,274,305,335])
def doy_of(d): return int(CUM_LEAP[d.month-1]+d.day)

def circ_smooth(a):
    trip=np.concatenate([a,a,a],axis=0); c=np.cumsum(trip,axis=0)
    out=np.empty_like(a)
    for k in range(366):
        out[k]=(c[k+366+15]-c[k[k:=k]]*0 + c[k+366+15]-c[k+366-16])/31.0
    return out

def circ_smooth(a):
    trip=np.concatenate([a,a,a],axis=0); c=np.cumsum(trip,axis=0)
    out=np.empty_like(a)
    for k in range(366):
        out[k]=(c[k+366+15]-c[k+366-16])/31.0
    return out

thr=np.full((367,60,60), np.nan); thr[1:]=circ_smooth(thr_raw[1:])
hot=np.zeros(target.shape, dtype=bool)
for k in range(target.shape[0]):
    hot[k]=target[k]>=thr[doy_of(t_start+dt.timedelta(days=k))]
print('hot fraction over sea cells:', float(hot[:,sea].mean()))

def cell_mhw(h):
    m=np.zeros(h.size, dtype=bool)
    idx=np.flatnonzero(h)
    if idx.size==0: return m
    br=np.flatnonzero(np.diff(idx)>1)
    starts=np.r_[idx[0], idx[br+1]]; ends=np.r_[idx[br], idx[-1]]
    keep=(ends-starts+1)>=5
    if not keep.any(): return m
    s=starts[keep]; e=ends[keep]
    ms=[int(s[0])]; me=[int(e[0])]
    for k in range(1,len(s)):
        if s[k]-me[-1]-1<=2: me[-1]=int(e[k])
        else: ms.append(int(s[k])); me.append(int(e[k]))
    for a,b in zip(ms,me): m[a:b+1]=True
    return m

t0=time.time()
mhw=np.zeros(hot.shape, dtype=bool)
for i in range(60):
    for j in range(60):
        if sea[i,j]:
            mhw[:,i,j]=cell_mhw(hot[:,i,j])
print('cell loop seconds:', round(time.time()-t0,1))
mp=mhw[:,sea].sum(axis=0)
print('cells with >=1 MHW day:', int((mp>0).sum()), '/', int(sea.sum()))
print('MHW days per cell: min', int(mp.min()), 'max', int(mp.max()), 'mean', round(float(mp.mean()),3))
print('total MHW cell-days:', int(mhw.sum()))

active=mhw.any(axis=(1,2))
idx=np.flatnonzero(active)
ev=[]
if idx.size:
    br=np.flatnonzero(np.diff(idx)>1)
    starts=np.r_[idx[0], idx[br+1]]; ends=np.r_[idx[br], idx[-1]]
    ev=[(int(a),int(b)) for a,b in zip(starts,ends)]
print('active days:', int(active.sum()), 'of', active.size)
events=[{'onset':str(t_start+dt.timedelta(days=a)),'end':str(t_start+dt.timedelta(days=b))} for a,b in ev]
for e in events: print(e, ' length', (dt.date.fromisoformat(e['end'])-dt.date.fromisoformat(e['onset'])).days+1)

np.savez_compressed('/work/final.npz', sea=sea, hot=hot, mhw=mhw, active=active)
with open('/work/events.json','w') as fh: json.dump(events, fh)
print('saved final arrays & events')
