code=r'''
import numpy as np, pandas as pd, xarray as xr, json, os
z=np.load("/tmp/sub.npz")
A=z["sst"]; dates=pd.to_datetime(z["dates"]); lat=z["lat"]; lon=z["lon"]
dates=pd.DatetimeIndex(dates)
def doy(t):
    if t.month==2 and t.day==29: return 60
    d=t.dayofyear
    if t.is_leap_year and t > pd.Timestamp(t.year,2,29): d-=1
    return d
dd=np.array([doy(t) for t in dates])
pos={t:i for i,t in enumerate(dates)}
base=pd.date_range("1992-01-01","2002-12-31")
sets={d:set() for d in range(1,367)}
for b in base:
    d=doy(b)
    for k in range(-5,6):
        x=b+pd.Timedelta(days=k)
        sets[d].add(pos[x])
thr=np.full((367,60,60),np.nan); clim=np.full((367,60,60),np.nan)
for d in range(1,367):
    if d==60: continue
    idx=sorted(sets[d])
    V=A[idx]
    thr[d]=np.nanquantile(V,0.9,axis=0,method="hazen")
    clim[d]=np.nanmean(V,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(x):
    y=np.empty_like(x[1:])
    base_=x[1:]
    out=np.empty((366,)+x.shape[1:])
    for d in range(366):
        ids=[(d+k)%366 for k in range(-15,16)]
        out[d]=base_[ids].mean(axis=0)
    return out
T=smooth(thr); C=smooth(clim)
# target
tmask=(dates>=pd.Timestamp("2012-06-01"))&(dates<=pd.Timestamp("2012-08-31"))
ti=np.where(tmask)[0]
S=A[ti]; tdates=dates[ti]; tdoy=dd[ti]
sea=np.all(np.isfinite(S),axis=0)
hot=np.zeros(S.shape,bool)
for i,d in enumerate(tdoy):
    hot[i]=(S[i]>=T[d-1])
hot&=sea[None]
mhw=np.zeros(S.shape,bool)
nT=len(ti)
for y in range(60):
    for x in range(60):
        if not sea[y,x]: continue
        h=hot[:,y,x]
        # runs
        runs=[];i=0
        while i<nT:
            if h[i]:
                j=i
                while j+1<nT and h[j+1]: j+=1
                if j-i+1>=5: runs.append([i,j])
                i=j+1
            else: i+=1
        # join gaps 1-2
        merged=[]
        for r in runs:
            if merged and r[0]-merged[-1][1]-1<=2:
                merged[-1][1]=r[1]
            else: merged.append(list(r))
        for a,b in merged: mhw[a:b+1,y,x]=True
active=mhw.any(axis=(1,2))
events=[];i=0
while i<nT:
    if active[i]:
        j=i
        while j+1<nT and active[j+1]: j+=1
        events.append({"onset":str(tdates[i].date()),"end":str(tdates[j].date())})
        i=j+1
    else: i+=1
print("sea cells",sea.sum(),"hot cells-days",hot.sum(),"mhw cell-days",mhw.sum())
print(events)
os.makedirs("/tmp/output",exist_ok=True)
print(sea.shape, T.shape)
np.savez("/tmp/res.npz",mhw=mhw,sea=sea,tdates=np.array([str(t.date()) for t in tdates]))
'''
open("/tmp/mhw.py","w").write(code)
r=subprocess.run("cd /tmp && python mhw.py",shell=True,capture_output=True,text=True); print(r.stdout, r.stderr[-3000:])