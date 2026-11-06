
script = r'''
import numpy as np, datetime as dt, json, os, warnings
import xarray as xr
z=np.load('/tmp/sub.npz')
S=z['S']; lat=z['lat']; lon=z['lon']; dates=[dt.date.fromisoformat(s) for s in z['dates']]
idx={d:i for i,d in enumerate(dates)}
def doy(d):
    if d.month==2 and d.day==29: return 60
    n=(dt.date(2001,d.month,d.day)-dt.date(2001,1,1)).days+1
    return n if d.month<=2 else n+1
assert doy(dt.date(1992,2,28))==59 and doy(dt.date(1992,3,1))==61 and doy(dt.date(1992,12,31))==366 and doy(dt.date(1993,12,31))==366
baseline=[dt.date(1992,1,1)+dt.timedelta(i) for i in range((dt.date(2002,12,31)-dt.date(1992,1,1)).days+1)]
pool_dates={d:set() for d in range(1,367) if d!=60}
for b in baseline:
    k=doy(b)
    if k==60: continue
    for off in range(-5,6):
        pool_dates[k].add(b+dt.timedelta(off))
thr=np.full((367,60,60),np.nan); clim=np.full((367,60,60),np.nan)
for k,ds_ in pool_dates.items():
    assert all(x in idx for x in ds_)
    arr=np.stack([S[idx[x]] for x in sorted(ds_)])
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        thr[k]=np.nanquantile(arr,0.9,axis=0,method='hazen')
        clim[k]=np.nanmean(arr,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    b=a[1:367]; out=np.zeros_like(b)
    for s in range(-15,16):
        out+=np.roll(b,-s,axis=0)
    out/=31
    res=np.full_like(a,np.nan); res[1:367]=out; return res
thrS=smooth(thr)
tgt=[]; d=dt.date(2013,6,1)
while d<=dt.date(2013,8,31): tgt.append(d); d+=dt.timedelta(1)
ti=[idx[d] for d in tgt]
T=S[ti]
sea=np.all(np.isfinite(T),axis=0)
print('tgt days',len(tgt),'sea cells',sea.sum(),'partial-nan',(np.isfinite(T).any(0)&~sea).sum())
doys=np.array([doy(d) for d in tgt])
TH=thrS[doys]
hot=(T>=TH)&sea[None]
ndays=len(tgt)
mask=np.zeros((ndays,60,60),bool)
for i in range(60):
    for j in range(60):
        if not sea[i,j]: continue
        h=hot[:,i,j]
        runs=[]; k=0
        while k<ndays:
            if h[k]:
                s=k
                while k<ndays and h[k]: k+=1
                if k-s>=5: runs.append([s,k-1])
            else: k+=1
        merged=[]
        for r in runs:
            if merged and (r[0]-merged[-1][1]-1) in (1,2): merged[-1][1]=r[1]
            else: merged.append(list(r))
        for s,e in merged: mask[s:e+1,i,j]=True
active=mask.any(axis=(1,2))
events=[]; k=0
while k<ndays:
    if active[k]:
        s=k
        while k<ndays and active[k]: k+=1
        events.append({"onset":tgt[s].isoformat(),"end":tgt[k-1].isoformat()})
    else: k+=1
print(events)
print('active days',active.sum(),'mask cell-days',mask.sum(),'hot cell-days',hot.sum())
os.makedirs('output',exist_ok=True)
tcoord=np.array([np.datetime64(d,'ns') for d in tgt])
ds_out=xr.Dataset({'mhw':(('time','lat','lon'),mask.astype(np.uint8))},
    coords={'time':tcoord,'lat':lat.astype(np.float64),'lon':lon.astype(np.float64)})
ds_out.to_netcdf('output/mhw_mask.nc')
rep={"region":{"lat_min":64.39,"lat_max":65.59,"lon_min":23.41,"lon_max":24.61},
 "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
 "target_analysed":{"start":"2013-06-01","end":"2013-08-31"},
 "events":events,"complete":True,
 "caveats":"Subset read from daily files; baseline pool uses calendar windows (+-5 d) incl. 1991-12-27..31 and 2003-01-01..05; non-sea cells (NaN on some target day) set to 0; grid coordinates are float32 values from dataset cast to float64. Some daily files listing was capped at 1000 but all needed files were accessed directly."}
json.dump(rep,open('output/report.json','w'),indent=2)
print(json.dumps(rep)[:1500])
'''
open('/tmp/run.py','w').write(script)
import subprocess
r=subprocess.run(['python','/tmp/run.py'],capture_output=True,text=True,cwd='/tmp')
print(r.stdout[-6000:], r.stderr[-3000:])
