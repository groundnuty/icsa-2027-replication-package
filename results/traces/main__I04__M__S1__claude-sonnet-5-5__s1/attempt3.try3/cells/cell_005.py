def doy(x):
    return (x-dt.date(2000,1,1)).days+1 if True else 0
def doy(x):
    return (dt.date(2000,x.month,x.day)-dt.date(2000,1,1)).days+1
idx={x:i for i,x in enumerate(bd)}
dd=np.array([doy(x) for x in bd])
thr=np.full((366,60,60),np.nan);clim=thr.copy()
for k in range(1,367):
    if k==60: continue
    ii=[]
    for x in bd:
        if dt.date(1992,1,1)<=x<=dt.date(2002,12,31) and doy(x)==k:
            ii+= [idx[x]+o for o in range(-5,6)]
    pool=B[ii]
    thr[k-1]=np.nanquantile(pool,0.9,axis=0,method='hazen')
    clim[k-1]=np.nanmean(pool,axis=0)
for a in (thr,clim): a[59]=(a[58]+a[60])/2
def sm(a):
    return np.mean([np.roll(a,-s,axis=0) for s in range(-15,16)],axis=0)
thr=sm(thr)
sea=np.isfinite(T).all(0)
dT=np.array([doy(x)-1 for x in td])
hot=(T>=thr[dT])&sea
def runs(h):
    out=np.zeros_like(h)
    for i in range(h.shape[1]):
        for j in range(h.shape[2]):
            v=h[:,i,j]
            if not v.any(): continue
            segs=[];s=None
            for t in range(len(v)+1):
                if t<len(v) and v[t]:
                    if s is None:s=t
                elif s is not None:
                    if t-s>=5:segs.append([s,t-1])
                    s=None
            m=[]
            for sg in segs:
                if m and sg[0]-m[-1][1]-1<=2: m[-1][1]=sg[1]
                else: m.append(sg)
            for a,b in m: out[a:b+1,i,j]=True
    return out
M=runs(hot)
act=M.any((1,2))
ev=[];s=None
for t in range(93):
    if t<92 and act[t]:
        if s is None:s=t
    elif s is not None: ev.append((str(td[s]),str(td[t-1])));s=None
print(sea.sum(),ev,M.sum())