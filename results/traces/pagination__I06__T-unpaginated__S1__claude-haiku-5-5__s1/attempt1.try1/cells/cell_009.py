code = r'''
import numpy as np, datetime as dt, json, xarray
def daterange(a,b):
    d=a
    while d<=b:
        yield d; d+=dt.timedelta(days=1)
z=np.load('work/sub.npz')
sst=z['sst']; dates=[dt.date.fromisoformat(s) for s in z['dates']]; lat=z['lat']; lon=z['lon']
idx={d:i for i,d in enumerate(dates)}
def doy(d):
    return (dt.date(2000,d.month,d.day)-dt.date(2000,1,1)).days+1
base_s,base_e=dt.date(1992,1,1),dt.date(2002,12,31)
pools={d:set() for d in range(1,367) if d!=60}
for b in daterange(base_s,base_e):
    dd=doy(b)
    if dd==60: continue
    for k in range(-5,6):
        pools[dd].add(b+dt.timedelta(days=k))
ny,nx=lat.size,lon.size
thr=np.full((367,ny,nx),np.nan); clim=np.full((367,ny,nx),np.nan)
for d,ds_ in pools.items():
    ii=[idx[x] for x in sorted(ds_)]
    vals=sst[ii]
    with np.errstate(all='ignore'):
        thr[d]=np.nanquantile(vals,0.9,axis=0,method='hazen')
        clim[d]=np.nanmean(vals,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    out=np.full_like(a,np.nan)
    for d in range(1,367):
        ks=[((d-1+k)%366)+1 for k in range(-15,16)]
        out[d]=np.mean(a[ks],axis=0)
    return out
thr_s=smooth(thr); clim_s=smooth(clim)
tgt=[i for i,d in enumerate(dates) if d>=dt.date(2012,6,1)]
T=sst[tgt]
sea=np.all(np.isfinite(T),axis=0)
print('sea cells',sea.sum(),'of',sea.size)
tdates=[dates[i] for i in tgt]
doys=np.array([doy(d) for d in tdates])
thr_t=thr_s[doys]
print('thr finite on sea', np.isfinite(thr_t[:,sea]).all(), 'clim finite', np.isfinite(clim_s[doys][:,sea]).all())
with np.errstate(invalid='ignore'):
    hot=(T>=thr_t)&sea[None]
mhw=np.zeros(T.shape,bool)
def runs(b):
    r=[];i=0;n=len(b)
    while i<n:
        if b[i]:
            j=i
            while j+1<n and b[j+1]: j+=1
            r.append([i,j]); i=j+1
        else: i+=1
    return r
for y in range(ny):
    for x in range(nx):
        if not sea[y,x]: continue
        ev=[r for r in runs(hot[:,y,x]) if r[1]-r[0]+1>=5]
        merged=[]
        for r in ev:
            if merged and (r[0]-merged[-1][1]-1) in (1,2):
                merged[-1][1]=r[1]
            else: merged.append(list(r))
        for a,bb in merged: mhw[a:bb+1,y,x]=True
active=mhw.any(axis=(1,2))
events=[];i=0
while i<len(active):
    if active[i]:
        j=i
        while j+1<len(active) and active[j+1]: j+=1
        events.append((tdates[i],tdates[j])); i=j+1
    else: i+=1
print('events',[(str(a),str(b)) for a,b in events])
print('mhw cell-days',mhw.sum(), 'hot cell-days',hot.sum(), 'active days', active.sum())
np.savez('work/res.npz', mhw=mhw, tdates=np.array([str(d) for d in tdates]), lat=lat, lon=lon, sea=sea)
'''
open('work/mhw.py','w').write(code)
exec(compile(code,'mhw','exec'))