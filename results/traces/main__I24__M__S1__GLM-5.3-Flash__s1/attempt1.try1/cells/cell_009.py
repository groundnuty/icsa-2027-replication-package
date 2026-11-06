import numpy as np, datetime as dt, time as time_mod

A=np.load('/tmp/A_all.npy')          # (4632, 60, 60) float64, 1991-12-27..2004-08-31
ords=np.load('/tmp/dates_ord.npy')
dates=[dt.date.fromordinal(int(o)) for o in ords]
T=A.shape[0]
Aflat=A.reshape(T,-1)                # (T, 3600)
NC=Aflat.shape[1]

def doy_map(d):
    y=d.timetuple().tm_yday
    leap = d.year%4==0 and (d.year%100!=0 or d.year%400==0)
    return y if leap else (y+1 if y>=60 else y)
doy=np.array([doy_map(d) for d in dates])

b0=dt.date(1992,1,1); b1=dt.date(2002,12,31)
base_idx=np.array([i for i,d in enumerate(dates) if b0<=d<=b1])
base_doy=doy[base_idx]
list_d={d: base_idx[base_doy==d] for d in range(1,367)}
counts={d:len(v) for d,v in list_d.items()}
import collections
print('pool date counts: histogram', collections.Counter(counts.values()))
print('count d=1',counts[1],'d=59',counts[59],'d=60',counts[60],'d=61',counts[61],'d=366',counts[366])

offs=np.arange(-5,6)
thr_raw=np.full((366,NC),np.nan)
clim_raw=np.full((366,NC),np.nan)
t0=time_mod.time()
rows=np.arange(NC)
for d in range(1,367):
    idxs=list_d[d]
    if len(idxs)==0:
        continue
    P=Aflat[idxs[:,None]+offs[None,:],:]           # (nd, 11, 3600)
    P=np.ascontiguousarray(P.reshape(len(idxs)*11,NC).T)  # (NC, pool)
    fin=np.isfinite(P)
    nv=fin.sum(axis=1)
    S=np.sort(np.where(fin,P,np.inf),axis=1)
    pos0=(nv-1)*0.9
    k1=np.floor(pos0).astype(np.int64)
    gam=pos0-k1
    x1=S[rows,k1]
    x2=np.where(gam>0, S[rows,k1+1], x1)
    q=x1+gam*(x2-x1)
    q[nv==0]=np.nan
    thr_raw[d-1]=q
    with np.errstate(invalid='ignore'):
        clim_raw[d-1]=np.nanmean(P,axis=1)
print('pool loop %.1fs'%(time_mod.time()-t0))
print('NaNs in thr_raw before fill: doy60 nan?', np.isnan(thr_raw[59]).all(), 'others', np.isnan(thr_raw).sum())
print('NaNs in clim_raw before fill:', np.isnan(clim_raw).sum())
# fill day 60 with mean of 59 and 61
thr_raw[59]=0.5*(thr_raw[58]+thr_raw[60])
clim_raw[59]=0.5*(clim_raw[58]+clim_raw[60])
print('NaNs after fill: thr',np.isnan(thr_raw).sum(),'clim',np.isnan(clim_raw).sum())
np.save('/tmp/thr_raw.npy',thr_raw); np.save('/tmp/clim_raw.npy',clim_raw)
# spot check one cell
c=0
print('cell0 thr doy1,60,152,366:',thr_raw[[0,59,152,365],0])
print('cell0 clim doy1,60,152,366:',clim_raw[[0,59,152,365],0])
