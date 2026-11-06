script2 = r'''
import numpy as np, datetime as dt, json, os, xarray as xr
g=np.load('/work/grid.npz'); lat=g['lat']; lon=g['lon']
def doy(d):
    # leap-style mapping: 29 Feb -> 60 always
    if d.month==2 and d.day==29: return 60
    nd=dt.date(2001,d.month,d.day)  # non-leap calendar
    n=(nd-dt.date(2001,1,1)).days+1
    if d.month>2 or (d.month==2 and d.day>29): pass
    return n if (d.month<2 or (d.month==2 and d.day<29)) else n+1
assert doy(dt.date(2001,2,28))==59 and doy(dt.date(2000,2,29))==60 and doy(dt.date(2001,3,1))==61 and doy(dt.date(2001,12,31))==366
def load(d):
    return np.load(f"/work/cache/{d.strftime('%Y%m%d')}.npy").astype(np.float64)
# all baseline dates available (incl. extension)
ext0=dt.date(1991,12,27); ext1=dt.date(2003,1,5)
alld=[]; d=ext0
while d<=ext1: alld.append(d); d+=dt.timedelta(1)
stack={}
for d in alld: stack[d]=load(d)
bstart=dt.date(1992,1,1); bend=dt.date(2002,12,31)
ny,nx=lat.size,lon.size
thr=np.full((367,ny,nx),np.nan); clim=np.full((367,ny,nx),np.nan)
# pools
pools={k:[] for k in range(1,367) if k!=60}
base_dates=[]
d=bstart
while d<=bend: base_dates.append(d); d+=dt.timedelta(1)
for b in base_dates:
    k=doy(b)
    if k==60: continue
    for off in range(-5,6):
        t=b+dt.timedelta(off)
        pools[k].append(stack[t])
for k in range(1,367):
    if k==60: continue
    P=np.stack(pools[k])  # n x ny x nx
    thr[k]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim[k]=np.nanmean(P,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(A):
    a=A[1:367]  # days 1..366 index 0..365
    out=np.empty_like(a)
    for i in range(366):
        idx=[(i+o)%366 for o in range(-15,16)]
        out[i]=np.mean(a[idx],axis=0)
    return out
T=smooth(thr); C=smooth(clim)
thr=np.full((367,ny,nx),np.nan); thr[1:]=T
clim=np.full((367,ny,nx),np.nan); clim[1:]=C
np.savez('/work/thr.npz',thr=thr,clim=clim)
print('pool size example', len(pools[100]), 'nan thr cells', np.isnan(thr[1:]).any(axis=0).sum())
'''
open('/work/thr.py','w').write(script2)
import subprocess
p=subprocess.run(['python','/work/thr.py'],capture_output=True,text=True,timeout=3000)
print(p.stdout[-3000:], p.stderr[-3000:])