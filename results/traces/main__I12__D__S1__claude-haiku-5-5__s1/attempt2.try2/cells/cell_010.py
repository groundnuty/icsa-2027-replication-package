
script = r'''
import numpy as np, datetime as dt, json, os, glob
import xarray as xr
os.makedirs('/work/output',exist_ok=True)
D0=dt.date(1991,12,27); D1=dt.date(2003,1,5)
ndays=(D1-D0).days+1
dates=[D0+dt.timedelta(days=i) for i in range(ndays)]
# load region subsets
sst_all=[]; lat=None; lon=None
for d in dates:
    z=np.load(f'/work/sub/{d:%Y%m%d}.npz')
    assert z['time'].item()==d.isoformat(), (d, z['time'])
    sst_all.append(z['sst'].astype(np.float64))
    if lat is None: lat=z['lat']; lon=z['lon']
S=np.stack(sst_all)  # (ndays, nlat, nlon)
print('shape',S.shape, 'nan frac', np.isnan(S).mean(), 'min', np.nanmin(S), 'max', np.nanmax(S))
def doy(d):
    return d.replace(year=2000).timetuple().tm_yday
doys=np.array([doy(d) for d in dates])
# baseline dates
B0=dt.date(1992,1,1); B1=dt.date(2002,12,31)
base_dates=[d for d in dates if B0<=d<=B1]
ncell=S.shape[1]*S.shape[2]
S2=S.reshape(ndays,-1)
thr=np.full((367,ncell),np.nan); clim=np.full((367,ncell),np.nan)
idx_of={d:i for i,d in enumerate(dates)}
for d in range(1,367):
    if d==60: continue
    bd=[b for b in base_dates if doy(b)==d]
    if not bd: continue
    pool_dates=set()
    for b in bd:
        for k in range(-5,6):
            t=b+dt.timedelta(days=k)
            if t in idx_of: pool_dates.add(t)
    ii=sorted(idx_of[t] for t in pool_dates)
    P=S2[ii]
    with np.errstate(all='ignore'):
        thr[d]=np.nanquantile(P,0.9,axis=0,method='hazen')
        clim[d]=np.nanmean(P,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    a=a[1:367]  # 366 entries, index 0 = doy1
    out=np.zeros_like(a)
    for k in range(-15,16):
        out+=np.roll(a,-k,axis=0)
    return out/31.0
thr_s=smooth(thr); clim_s=smooth(clim)
# target
T0=dt.date(2009,6,1); T1=dt.date(2009,8,31)
tdates=[d for d in dates if T0<=d<=T1]
ti=[idx_of[d] for d in tdates]
St=S2[ti]  # (ntarget, ncell)
sea=np.all(np.isfinite(St),axis=0)
print('sea cells', sea.sum(), 'of', ncell)
tdoy=np.array([doy(d) for d in tdates])
thr_t=thr_s[tdoy-1]  # (ntarget,ncell)
with np.errstate(invalid='ignore'):
    hot=(St>=thr_t)&np.isfinite(thr_t)
hot&=sea[None,:]
nt=len(tdates)
mhw=np.zeros((nt,ncell),bool)
for c in np.where(sea)[0]:
    h=hot[:,c]
    # runs of >=5 hot days
    events=[]; i=0
    while i<nt:
        if h[i]:
            j=i
            while j+1<nt and h[j+1]: j+=1
            if j-i+1>=5: events.append([i,j])
            i=j+1
        else: i+=1
    # join events separated by 1 or 2 non-hot days
    merged=[]
    for e in events:
        if merged and (e[0]-merged[-1][1]-1) in (1,2):
            merged[-1][1]=e[1]
        else: merged.append(list(e))
    for s,e in merged: mhw[s:e+1,c]=True
active=mhw.any(axis=1)
events=[]; i=0
while i<nt:
    if active[i]:
        j=i
        while j+1<nt and active[j+1]: j+=1
        events.append((tdates[i].isoformat(), tdates[j].isoformat()))
        i=j+1
    else: i+=1
print('events', events)
print('per-day active count', mhw.sum(axis=1))
# write mask
import xarray as xr
mask=mhw.reshape(nt,S.shape[1],S.shape[2]).astype(np.uint8)
mask=xr.DataArray(mask,dims=('time','lat','lon'),coords={'time':np.array(tdates,dtype='datetime64[ns]'),'lat':lat,'lon':lon},name='mhw')
mask.to_netcdf('/work/output/mhw_mask.nc')
rep={'region':{'lat_min':56.09,'lat_max':57.29,'lon_min':10.55,'lon_max':11.75},
     'baseline_analysed':{'start':'1992-01-01','end':'2002-12-31'},
     'target_analysed':{'start':'2009-06-01','end':'2009-08-31'},
     'events':[{'onset':a,'end':b} for a,b in events],
     'complete':True,
     'caveats':'Baseline pool uses dates 1991-12-27..2003-01-05 windows; day 60 handled as mean of 59 and 61; per-cell MHW gap joining applied to hot runs >=5 days; SST float32 decoded values promoted to float64.'}
json.dump(rep,open('/work/output/report.json','w'),indent=2)
print('written; lat', lat[:3], lat[-2:], 'lon', lon[:3], lon[-2:], 'sea', sea.sum())
'''
open('/work/an.py','w').write(script)
import subprocess
r=subprocess.run(['python','/work/an.py'],capture_output=True,text=True,timeout=3000)
print(r.stdout[-6000:], r.stderr[-3000:])