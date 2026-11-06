
import numpy as np, json, os, warnings
warnings.filterwarnings('ignore')
z=np.load('/tmp/sst.npz')
sst=z['sst']; lat=z['lat']; lon=z['lon']; alld=z['dates'].astype('datetime64[D]')
ndays,nla,nlo=sst.shape
D=lambda s: np.datetime64(s)
def doy(dt):
    # leap-year calendar (2000): 29 Feb=60, 1 Mar=61, 31 Dec=366
    y=np.datetime64('2000-01-01')
    m=dt.astype('datetime64[D]')
    md=(m.astype('datetime64[D]')-m.astype('datetime64[Y]').astype('datetime64[D]'))
    mm=m.astype('datetime64[M]')
    mday=(m-mm.astype('datetime64[D]')).astype(int)
    lm=(mm.astype(int)%12)+1
    return (np.datetime64('2000-01-01')+ (np.datetime64('2000-%02d-%02d'%(lm,mday+1))-np.datetime64('2000-01-01'))).astype(int)  # placeholder
# simpler explicit doy using 2000 calendar
def doy2(d):
    d=np.datetime64(d,'D')
    lm=int(str(d)[5:7]); dd=int(str(d)[8:10])
    return int((np.datetime64('2000-%02d-%02d'%(lm,dd))-np.datetime64('2000-01-01')).astype(int))+1
base_lo,base_hi=D('1992-01-01'),D('2002-12-31')
idx_of={str(d):i for i,d in enumerate(alld)}
pools={d:set() for d in range(1,367) if d!=60}
bdates=np.arange(base_lo,base_hi+np.timedelta64(1,'D'))
for b in bdates:
    dd=doy2(b)
    if dd==60: continue
    for off in range(-5,6):
        t=str(b+np.timedelta64(off,'D'))
        pools[dd].add(idx_of[t])
thr=np.full((367,nla,nlo),np.nan); clim=np.full((367,nla,nlo),np.nan)
for dd in pools:
    if dd==60: continue
    ii=sorted(pools[dd])
    arr=sst[ii]
    thr[dd]=np.nanquantile(arr,0.9,axis=0,method='hazen')
    clim[dd]=np.nanmean(arr,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):  # a: (367,...) index 1..366
    b=a[1:367]
    out=np.zeros_like(b)
    for k in range(-15,16):
        out+=np.roll(b,-k,axis=0)
    out/=31
    res=np.full_like(a,np.nan); res[1:367]=out; return res
thr_s=smooth(thr); clim_s=smooth(clim)
print('pool sizes check', len(pools[1]), len(pools[59]), len(pools[366]))
print('NaN thr sea-cell count', np.isnan(thr_s[1:367]).sum())
# target
tmask=np.array([str(d).startswith('2014-') and '2014-06-01'<=str(d)<='2014-08-31' for d in alld])
tidx=np.where(tmask)[0]
tsst=sst[tidx]; tdates_=alld[tidx]
sea=np.isfinite(tsst).all(axis=0)
print('target days',len(tidx), tdates_[0], tdates_[-1],'sea cells',sea.sum(),'of',nla*nlo)
doys=np.array([doy2(d) for d in tdates_])
T=thr_s[doys]  # (92,60,60)
hot=(tsst>=T)&sea[None]
mhw=np.zeros_like(hot)
def runs(b):
    r=[]; n=len(b); i=0
    while i<n:
        if b[i]:
            j=i
            while j+1<n and b[j+1]: j+=1
            r.append([i,j]); i=j+1
        else: i+=1
    return r
for a in range(nla):
    for c in range(nlo):
        if not sea[a,c]: continue
        rr=[x for x in runs(hot[:,a,c]) if x[1]-x[0]+1>=5]
        if not rr: continue
        merged=[rr[0][:]]
        for s,e in rr[1:]:
            if s-merged[-1][1]-1<=2: merged[-1][1]=e
            else: merged.append([s,e])
        for s,e in merged: mhw[s:e+1,a,c]=True
active=mhw.any(axis=(1,2))
events=[]; i=0; n=len(active)
while i<n:
    if active[i]:
        j=i
        while j+1<n and active[j+1]: j+=1
        events.append((str(tdates_[i]),str(tdates_[j]))); i=j+1
    else: i+=1
print('events',events)
print('mhw cell-days',mhw.sum(),'active days',active.sum())
