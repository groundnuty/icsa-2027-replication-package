code = r'''
import os, json, datetime as dt, numpy as np, xarray as xr
os.makedirs('/work/output', exist_ok=True) if False else None
os.makedirs('/work/output', exist_ok=True)
S={}
lat=lon=None
for f in os.listdir('/work/sub'):
    z=np.load('/work/sub/'+f)
    dstr=str(z['date']); assert f[:8]==dstr.replace('-',''), f
    S[dt.date.fromisoformat(dstr)]=z['sst']
    lat=z['lat']; lon=z['lon']
print('loaded',len(S), lat.shape, lon.shape, lat[0],lat[-1],lon[0],lon[-1])
NLAT,NLON=len(lat),len(lon)

def doy(d):
    # leap-year table: Feb29=60 always, Dec31=366 always
    ly=dt.date(2000,d.month,d.day)  # 2000 is leap
    return (ly-dt.date(2000,1,1)).days+1

# baseline pools
B0=dt.date(1992,1,1); B1=dt.date(2002,12,31)
base_days=[B0+dt.timedelta(i) for i in range((B1-B0).days+1)]
thr_raw=np.full((367,NLAT,NLON),np.nan); clim_raw=np.full((367,NLAT,NLON),np.nan)
for d in range(1,367):
    if d==60: continue
    bdates=[b for b in base_days if doy(b)==d]
    win=set()
    for b in bdates:
        for k in range(-5,6):
            win.add(b+dt.timedelta(k))
    win=sorted(win)
    arr=np.stack([S[w] for w in win])  # (n,lat,lon)
    with np.errstate(all='ignore'):
        thr_raw[d]=np.nanquantile(arr,0.9,axis=0,method='hazen')
        clim_raw[d]=np.nanmean(arr,axis=0)
thr_raw[60]=(thr_raw[59]+thr_raw[61])/2
clim_raw[60]=(clim_raw[59]+clim_raw[61])/2
thr_raw=thr_raw[1:]; clim_raw=clim_raw[1:]  # index 0 -> doy1
def smooth(a):
    out=np.empty_like(a)
    for i in range(366):
        idx=[(i+k)%366 for k in range(-15,16)]
        out[i]=np.mean(a[idx],axis=0)
    return out
thr=smooth(thr_raw); clim=smooth(clim_raw)
print('thr nan cells', np.isnan(thr[0]).sum())

# target
T0=dt.date(2004,6,1); T1=dt.date(2004,8,31)
tdates=[T0+dt.timedelta(i) for i in range((T1-T0).days+1)]
sst=np.stack([S[d] for d in tdates])  # (T,lat,lon)
sea=np.all(np.isfinite(sst),axis=0)
print('sea cells',sea.sum(),'of',sea.size)
tdoy=np.array([doy(d) for d in tdates])
thr_t=thr[tdoy-1]  # (T,lat,lon)
with np.errstate(invalid='ignore'):
    hot=(sst>=thr_t)&sea[None]
T=len(tdates)
mhw=np.zeros((T,NLAT,NLON),np.uint8)
for i in range(NLAT):
    for j in range(NLON):
        if not sea[i,j]: continue
        h=hot[:,i,j]
        # hot runs
        runs=[]; t=0
        while t<T:
            if h[t]:
                s=t
                while t<T and h[t]: t+=1
                if t-s>=5: runs.append([s,t-1])
            else: t+=1
        # join runs separated by 1 or 2 non-hot days
        merged=[]
        for r in runs:
            if merged and (r[0]-merged[-1][1]-1)<=2:
                merged[-1][1]=r[1]
            else: merged.append(list(r))
        for s,e in merged: mhw[s:e+1,i,j]=1
active=mhw.any(axis=(1,2))
events=[]; t=0
while t<T:
    if active[t]:
        s=t
        while t<T and active[t]: t+=1
        events.append({'onset':tdates[s].isoformat(),'end':tdates[t-1].isoformat()})
    else: t+=1
print('events',events)
print('total mhw cell-days',int(mhw.sum()), 'active days', int(active.sum()))

os.makedirs('/work/output',exist_ok=True)
ds=xr.Dataset({'mhw':(('time','lat','lon'),mhw)},
  coords={'time':np.array(tdates,dtype='datetime64[ns]'),'lat':lat.astype(np.float32),'lon':lon.astype(np.float32)})
ds.to_netcdf('/work/output/mhw_mask.nc')
rep={'region':{'lat_min':63.31,'lat_max':64.51,'lon_min':21.31,'lon_max':22.51},
 'baseline_analysed':{'start':'1992-01-01','end':'2002-12-31'},
 'target_analysed':{'start':'2004-06-01','end':'2004-08-31'},
 'events':events,'complete':True,
 'caveats':'Baseline windows use files 1991-12-27..1992-01-05 and 2002-12-27..2003-01-05 (outside 1992-2002 only as window extensions). Region bounds reported as requested; actual grid cell centres are %.2f-%.2f N, %.2f-%.2f E. Non-sea cells (any NaN in target period) set to 0. Leap-year doy table used for all years (31 Dec = 366).'%(lat[0],lat[-1],lon[0],lon[-1])}
json.dump(rep,open('/work/output/report.json','w'),indent=1)
print('written')
'''
open('/work/analyse.py','w').write(code)
import subprocess
r=subprocess.run('cd /work && python analyse.py',shell=True,capture_output=True,text=True)
print(r.stdout[-5000:], r.stderr[-3000:])