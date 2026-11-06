code = r'''
import numpy as np, datetime as dt, json, os
import xarray as xr, pandas as pd
z=np.load('/tmp/sst_region.npz')
arr=z['arr']; days=[dt.date.fromisoformat(s) for s in z['days']]; latv=z['lat']; lonv=z['lon']
idx_of={dd:i for i,dd in enumerate(days)}
mdays=[31,29,31,30,31,30,31,31,30,31,30,31]
def doy(date):
    return sum(mdays[:date.month-1])+date.day
assert doy(dt.date(2001,2,28))==59 and doy(dt.date(2000,2,29))==60 and doy(dt.date(2001,3,1))==61 and doy(dt.date(2001,12,31))==366
bdates=[dt.date(1992,1,1)+dt.timedelta(i) for i in range((dt.date(2002,12,31)-dt.date(1992,1,1)).days+1)]
pool_dates={k:set() for k in range(1,367)}
for b in bdates:
    for off in range(-5,6):
        pool_dates[doy(b)].add(b+dt.timedelta(off))
thr=np.full((367,60,60),np.nan); clim=np.full((367,60,60),np.nan)
for k in range(1,367):
    if k==60: continue
    P_=arr[[idx_of[t] for t in sorted(pool_dates[k])]]
    with np.errstate(all='ignore'):
        thr[k]=np.nanquantile(P_,0.9,axis=0,method='hazen')
        clim[k]=np.nanmean(P_,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth366(a366):
    out=np.empty_like(a366)
    for d in range(366):
        out[d]=np.mean(a366[[((d+o)%366) for o in range(-15,16)]],axis=0)
    return out
thr366=smooth366(thr[1:]); clim366=smooth366(clim[1:])
tdates=[dt.date(2010,6,1)+dt.timedelta(i) for i in range((dt.date(2010,8,31)-dt.date(2010,6,1)).days+1)]
tsst=arr[[idx_of[t] for t in tdates]]
sea=np.all(np.isfinite(tsst),axis=0)
tdoy=np.array([doy(dd) for dd in tdates])
Th=thr366[tdoy-1]
with np.errstate(all='ignore'):
    hot=(tsst>=Th)&sea[None]&np.isfinite(Th)
nT,ny,nx=hot.shape
mhw=np.zeros((nT,ny,nx),bool)
for iy in range(ny):
    for ix in range(nx):
        if not sea[iy,ix]: continue
        h=hot[:,iy,ix]
        runs=[];i=0
        while i<nT:
            if h[i]:
                j=i
                while j+1<nT and h[j+1]: j+=1
                if j-i+1>=5: runs.append([i,j])
                i=j+1
            else: i+=1
        merged=[]
        for r in runs:
            if merged:
                g=r[0]-merged[-1][1]-1
                if 1<=g<=2 and not h[merged[-1][1]+1:r[0]].any():
                    merged[-1][1]=r[1]; continue
            merged.append(list(r))
        for a,b in merged: mhw[a:b+1,iy,ix]=True
active=mhw.any(axis=(1,2))
events=[];i=0
while i<nT:
    if active[i]:
        j=i
        while j+1<nT and active[j+1]: j+=1
        events.append({'onset':tdates[i].isoformat(),'end':tdates[j].isoformat()})
        i=j+1
    else: i+=1
print('sea',sea.sum(),'mhw cell-days',mhw.sum(),'events',events)
os.makedirs('output',exist_ok=True)
da=xr.DataArray(mhw.astype(np.uint8),dims=('time','lat','lon'),
    coords={'time':pd.to_datetime([d.isoformat() for d in tdates]),'lat':latv,'lon':lonv},name='mhw')
da.to_dataset().to_netcdf('output/mhw_mask.nc')
rep={'region':{'lat_min':57.13,'lat_max':58.33,'lon_min':22.79,'lon_max':23.99},
     'baseline_analysed':{'start':'1992-01-01','end':'2002-12-31'},
     'target_analysed':{'start':'2010-06-01','end':'2010-08-31'},
     'events':events,'complete':True,
     'caveats':'Pools use SST from 1991-12-27 to 2003-01-05 for +-5 day windows. Day 60 threshold and climatology are the mean of days 59 and 61 before smoothing. Region grid is 60x60 cells (lat 57.14-58.32, lon 22.80-23.98). Gap joining requires all gap days non-hot. Land cells and cells not finite on every target day are 0 in the mask.'}
json.dump(rep,open('output/report.json','w'),indent=2)
chk=xr.open_dataset('output/mhw_mask.nc')
print(chk.mhw.dims, chk.mhw.shape, chk.mhw.dtype, int(chk.mhw.sum()))
'''
open('/tmp/run.py','w').write(code)
import subprocess
r=subprocess.run(['python','/tmp/run.py'],capture_output=True,text=True,cwd='/tmp')
print(r.stdout, r.stderr[-2000:])