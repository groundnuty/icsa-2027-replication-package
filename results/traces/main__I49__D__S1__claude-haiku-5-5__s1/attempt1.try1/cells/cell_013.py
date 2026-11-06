cum=[0,31,59,90,120,151,181,212,243,273,304,334]  # days before month start in leap calendar
def doy(d):
    if d.month==2 and d.day==29: return 60
    base=[0,31,60,91,121,152,182,213,244,274,305,335][d.month-1]
    # leap-calendar: Feb 29 = 60, Mar1=61
    return base+d.day
assert doy(dt.date(2001,2,28))==59 and doy(dt.date(2001,3,1))==61 and doy(dt.date(2001,12,31))==366 and doy(dt.date(2000,2,29))==60
# baseline dates
bdates=[dt.date(y,1,1)+dt.timedelta(k) for y in range(1992,2003) for k in range((dt.date(y+1,1,1)-dt.date(y,1,1)).days)]
pool_idx={d:[] for d in range(1,367)}
seen={d:set() for d in range(1,367)}
for b in bdates:
    d=doy(b)
    if d==60: continue
    for k in range(-5,6):
        x=b+dt.timedelta(k)
        if x not in seen[d]:
            seen[d].add(x); pool_idx[d].append(idx[x])
print(len(bdates), len(pool_idx[1]), len(pool_idx[366]), len(pool_idx[152]), len(pool_idx[60]))
print(min(alld) , 'extended ok')
# per-cell pools: compute threshold and climatology per doy
thr=np.full((367,)+sea.shape,np.nan); clim=np.full_like(thr,np.nan)
Sb=S  # all
for d in range(1,367):
    if d==60: continue
    P=S[pool_idx[d]]  # n,60,60
    with np.errstate(all='ignore'):
        thr[d]=np.nanquantile(P,0.9,axis=0,method='hazen')
        clim[d]=np.nanmean(P,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    a=a[1:367]  # 366 x ...
    out=np.empty_like(a)
    for i in range(366):
        ids=[(i+k)%366 for k in range(-15,16)]
        out[i]=a[ids].mean(axis=0)
    return out
thrS=smooth(thr); climS=smooth(clim)
print(thrS.shape, np.isnan(thrS[:,sea]).sum())