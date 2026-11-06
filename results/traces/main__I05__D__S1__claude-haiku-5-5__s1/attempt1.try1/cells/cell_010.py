script3 = r'''
import numpy as np, datetime as dt, json, os, xarray as xr
g=np.load('/work/grid.npz'); lat=g['lat']; lon=g['lon']
th=np.load('/work/thr.npz'); thr=th['thr']
def doy(d):
    if d.month==2 and d.day==29: return 60
    nd=dt.date(2001,d.month,d.day); n=(nd-dt.date(2001,1,1)).days+1
    return n if (d.month<2 or (d.month==2 and d.day<29)) else n+1
tdays=[]; d=dt.date(2021,6,1)
while d<=dt.date(2021,8,31): tdays.append(d); d+=dt.timedelta(1)
S=np.stack([np.load(f"/work/cache/{d.strftime('%Y%m%d')}.npy").astype(np.float64) for d in tdays])  # T,ny,nx
sea=np.all(np.isfinite(S),axis=0)
print('sea cells',sea.sum(),'of',sea.size)
ny,nx=lat.size,lon.size
T=len(tdays)
ks=np.array([doy(d) for d in tdays])
TH=thr[ks]  # T,ny,nx
hot=(S>=TH)&sea[None]
hot&=np.isfinite(TH)
mhw=np.zeros((T,ny,nx),bool)
def runs(v):
    # return list of (start,end) inclusive of True runs
    out=[]; n=len(v); i=0
    while i<n:
        if v[i]:
            j=i
            while j+1<n and v[j+1]: j+=1
            out.append((i,j)); i=j+1
        else: i+=1
    return out
nev=0
for a in range(ny):
    for b in range(nx):
        if not sea[a,b]: continue
        r=[x for x in runs(hot[:,a,b]) if x[1]-x[0]+1>=5]
        if not r: continue
        merged=[list(r[0])]
        for s,e in r[1:]:
            if s-merged[-1][1]-1 in (1,2): merged[-1][1]=e
            else: merged.append([s,e])
        for s,e in merged:
            mhw[s:e+1,a,b]=True; nev+=1
print('per-cell mhw segments',nev,'mhw cell-days',mhw.sum())
active=mhw.any(axis=(1,2))
ev=runs(active)
events=[{"onset":tdays[s].isoformat(),"end":tdays[e].isoformat()} for s,e in ev]
print(events)
os.makedirs('/work/out',exist_ok=True)
np.save('/work/out/mhw.npy',mhw.astype(np.uint8))
json.dump(events,open('/work/out/events.json','w'))
'''
open('/work/mhw.py','w').write(script3)
p=subprocess.run(['python','/work/mhw.py'],capture_output=True,text=True,timeout=3000)
print(p.stdout[-3000:], p.stderr[-3000:])