
script = r'''
import numpy as np, datetime as dt, json, os, warnings
warnings.filterwarnings('ignore')
g=np.load('/tmp/sub/grid.npz')
lat=g['lat']; lon=g['lon']
il=np.where((lat>=57.41)&(lat<=58.61))[0]; jl=np.where((lon>=18.69)&(lon<=19.89))[0]
LAT=lat[il]; LON=lon[jl]
start=dt.date(1991,12,27); end=dt.date(2004,8,31)
ndays=(end-start).days+1
dates=[start+dt.timedelta(i) for i in range(ndays)]
idx={d:i for i,d in enumerate(dates)}
cube=np.full((ndays,len(LAT),len(LON)),np.nan)
for i,d in enumerate(dates):
    cube[i]=np.load(f"/tmp/sub/{d:%Y%m%d}.npy").astype(np.float64)
def doy(d): return dt.date(2000,d.month,d.day).timetuple().tm_yday
tgt=[d for d in dates if dt.date(2004,6,1)<=d<=dt.date(2004,8,31)]
T=cube[[idx[d] for d in tgt]]
sea=np.all(np.isfinite(T),axis=0)
print('target days',len(tgt),'sea cells',sea.sum())
bdates=[dt.date(1992,1,1)+dt.timedelta(i) for i in range((dt.date(2002,12,31)-dt.date(1992,1,1)).days+1)]
pool_dates={d:set() for d in range(1,367)}
for b in bdates:
    k=doy(b)
    if k==60: continue
    for s in range(-5,6):
        pool_dates[k].add(b+dt.timedelta(s))
thr_raw=np.full((367,len(LAT),len(LON)),np.nan); clim_raw=np.full((367,len(LAT),len(LON)),np.nan)
for k in range(1,367):
    if k==60: continue
    ii=[idx[t] for t in sorted(pool_dates[k])]
    P=cube[ii]
    thr_raw[k]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim_raw[k]=np.nanmean(P,axis=0)
thr_raw[60]=(thr_raw[59]+thr_raw[61])/2
clim_raw[60]=(clim_raw[59]+clim_raw[61])/2
A_thr=thr_raw[1:]; A_clim=clim_raw[1:]
def smooth(A):
    out=np.empty_like(A)
    for d in range(366):
        ids=[(d+o)%366 for o in range(-15,16)]
        out[d]=A[ids].mean(axis=0)
    return out
thr=smooth(A_thr); clim=smooth(A_clim)
print('nan thr sea', np.isnan(thr[:,sea]).sum(), 'nan clim sea', np.isnan(clim[:,sea]).sum())
# per-cell MHW
ntg=len(tgt)
doys=np.array([doy(d) for d in tgt])
hot=np.zeros((ntg,len(LAT),len(LON)),bool)
for t in range(ntg):
    hot[t]=(T[t]>=thr[doys[t]-1])  # NaN -> False
mhw=np.zeros_like(hot)
ncell_events=0
for a in range(len(LAT)):
    for b in range(len(LON)):
        if not sea[a,b]: continue
        h=hot[:,a,b]
        # maximal hot runs
        runs=[]; t=0
        while t<ntg:
            if h[t]:
                s=t
                while t<ntg and h[t]: t+=1
                if t-s>=5: runs.append([s,t-1])
            else: t+=1
        # join runs separated by 1 or 2 non-hot days
        ev=[]
        for r in runs:
            if ev and (r[0]-ev[-1][1]-1) in (1,2):
                ev[-1][1]=r[1]
            else:
                ev.append(list(r))
        for s,e in ev:
            mhw[s:e+1,a,b]=True; ncell_events+=1
active=mhw.any(axis=(1,2))
events=[]; t=0
while t<ntg:
    if active[t]:
        s=t
        while t<ntg and active[t]: t+=1
        events.append((tgt[s],tgt[t-1]))
    else: t+=1
print('cell events',ncell_events,'active days',active.sum())
for e in events: print(e[0],e[1])
os.makedirs('/tmp/out',exist_ok=True)
np.savez('/tmp/out/res.npz', mhw=mhw, sea=sea, hot=hot, active=active)
json.dump({'events':[{'onset':e[0].isoformat(),'end':e[1].isoformat()} for e in events],
           'tgt':[d.isoformat() for d in tgt]}, open('/tmp/out/res.json','w'))
'''
open('/tmp/run.py','w').write(script)
import subprocess
r=subprocess.run(['python','/tmp/run.py'],capture_output=True,text=True)
print(r.stdout[-6000:], r.stderr[-3000:])
