
script = r'''
import numpy as np, datetime as dt, json, os
z=np.load('/tmp/sst.npz')
sst=z['sst'][:,0] if z['sst'].ndim==4 else z['sst']
lat=z['lat']; lon=z['lon']; ds_str=z['days']
dates=[dt.date(int(s[:4]),int(s[4:6]),int(s[6:])) for s in ds_str]
idx={d:i for i,d in enumerate(dates)}
def doy(d):
    return dt.date(2000,d.month,d.day).timetuple().tm_yday
assert doy(dt.date(2001,2,28))==59 and doy(dt.date(2001,3,1))==61 and doy(dt.date(2000,12,31))==366
base0,base1=dt.date(1992,1,1),dt.date(2002,12,31)
pool_idx={d:set() for d in range(1,367) if d!=60}
b=base0
while b<=base1:
    d=doy(b)
    if d!=60:
        for k in range(-5,6):
            pool_idx[d].add(idx[b+dt.timedelta(k)])
    b+=dt.timedelta(1)
ny,nx=sst.shape[1:]
thr=np.full((367,ny,nx),np.nan); clim=np.full((367,ny,nx),np.nan)
for d in pool_idx:
    sub=sst[sorted(pool_idx[d])]
    with np.errstate(all='ignore'):
        thr[d]=np.nanquantile(sub,0.9,axis=0,method='hazen')
        clim[d]=np.nanmean(sub,axis=0)
thr=thr[1:]; clim=clim[1:]
thr[59]=(thr[58]+thr[60])/2; clim[59]=(clim[58]+clim[60])/2
def smooth(a):
    out=np.empty_like(a)
    for d in range(366):
        out[d]=a[[(d+k)%366 for k in range(-15,16)]].mean(axis=0)
    return out
thr_s=smooth(thr)
tgt=[i for i,d in enumerate(dates) if dt.date(2010,6,1)<=d<=dt.date(2010,8,31)]
T=sst[tgt]; tdates=[dates[i] for i in tgt]
sea=np.all(np.isfinite(T),axis=0)
print('sea cells',sea.sum(),'of',sea.size,'target days',len(tdates))
print('sea cells with NaN threshold:',(sea & np.isnan(thr_s).any(axis=0)).sum())
doys=np.array([doy(d) for d in tdates])
H=(T>=thr_s[doys-1]) & sea[None]
mhw=np.zeros(H.shape,bool)
for y in range(ny):
    for x in range(nx):
        if not sea[y,x]: continue
        h=H[:,y,x]
        runs=[]; s=None
        for t in range(len(h)+1):
            v=h[t] if t<len(h) else False
            if v and s is None: s=t
            if (not v) and s is not None:
                if t-s>=5: runs.append([s,t-1])
                s=None
        merged=[]
        for r in runs:
            if merged and r[0]-merged[-1][1]-1 in (1,2): merged[-1][1]=r[1]
            else: merged.append(list(r))
        m=np.zeros(len(h),bool)
        for a,bb in merged: m[a:bb+1]=True
        mhw[:,y,x]=m
active=mhw.any(axis=(1,2))
print('active days',active.sum(),'mhw cell-days',mhw.sum())
events=[]; s=None
for t in range(len(active)+1):
    v=active[t] if t<len(active) else False
    if v and s is None: s=t
    if (not v) and s is not None:
        events.append((tdates[s].isoformat(),tdates[t-1].isoformat())); s=None
print(events)
os.makedirs('/tmp/output',exist_ok=True)
np.savez('/tmp/res.npz',mhw=mhw,tdates=np.array([d.strftime('%Y%m%d') for d in tdates]),lat=lat,lon=lon,sea=sea,events=np.array(events))
'''
open('/tmp/run.py','w').write(script)
import subprocess
r=subprocess.run(['python','/tmp/run.py'],capture_output=True,text=True)
print(r.stdout[-6000:], r.stderr[-2000:])
