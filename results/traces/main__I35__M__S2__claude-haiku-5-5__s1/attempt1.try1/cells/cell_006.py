
import os, json
os.makedirs('output',exist_ok=True)
def doy_of(dates):
    # 366-day calendar: Feb29=60, Mar1=61 (use year 2000 mapping)
    d=pd.DatetimeIndex(dates)
    m2000=pd.to_datetime({'year':2000,'month':d.month,'day':d.day})
    return np.asarray(m2000.dayofyear)
bt=pd.DatetimeIndex(b.time.values)
bdoy=doy_of(bt)
bvals=b.values.astype(np.float64)  # (n, ny, nx)
ny,nx=bvals.shape[1:]
base_mask=(bt>=pd.Timestamp('1992-01-01'))&(bt<=pd.Timestamp('2002-12-31'))
Bdates=bt[base_mask]
Bdoy=bdoy[base_mask]
thr=np.full((367,ny,nx),np.nan); clim=np.full((367,ny,nx),np.nan)
for d in range(1,367):
    if d==60: continue
    Bsel=Bdates[Bdoy==d]
    idx=[]
    for B in Bsel:
        w=pd.date_range(B-pd.Timedelta(days=5),B+pd.Timedelta(days=5))
        idx.extend(bt.get_indexer(w))
    idx=np.unique(np.array(idx))
    assert (idx>=0).all()
    pool=bvals[idx]
    with np.errstate(all='ignore'):
        thr[d]=np.nanpercentile(pool,90,axis=0,method='hazen')
        clim[d]=np.nanmean(pool,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a366):
    out=np.empty_like(a366)
    for d in range(1,367):
        ids=[((d-1+k)%366) for k in range(-15,16)]
        out[d-1]=np.mean(a366[ids],axis=0)
    return out
T=smooth(thr[1:]); C=smooth(clim[1:])  # index d-1
# target
tt=pd.DatetimeIndex(t.time.values); tdoy=doy_of(tt)
tv=t.values.astype(np.float64)
sea=np.all(np.isfinite(tv),axis=0)
print('sea cells',sea.sum(),'of',sea.size)
hot=(tv>=T[tdoy-1]) & sea[None]
# per-cell MHW
mhw=np.zeros(tv.shape,bool)
nT=tv.shape[0]
for i in range(ny):
    for j in range(nx):
        if not sea[i,j]: continue
        h=hot[:,i,j]
        # runs
        ev=[];k=0
        while k<nT:
            if h[k]:
                s=k
                while k<nT and h[k]: k+=1
                if k-s>=5: ev.append([s,k-1])
            else: k+=1
        # join gaps of 1-2 days
        merged=[]
        for e in ev:
            if merged and e[0]-merged[-1][1]-1 in (1,2):
                merged[-1][1]=e[1]
            else: merged.append(list(e))
        for s,e in merged: mhw[s:e+1,i,j]=True
active=mhw.any(axis=(1,2))
events=[];k=0
while k<nT:
    if active[k]:
        s=k
        while k<nT and active[k]: k+=1
        events.append({"onset":str(tt[s].date()),"end":str(tt[k-1].date())})
    else: k+=1
print(events, mhw.sum(), active.sum())
