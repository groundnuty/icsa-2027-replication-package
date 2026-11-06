code = r'''
import numpy as np, json, os, datetime as dt, xarray as xr
z=np.load('/tmp/data.npz')
S=z['S']; dates=z['dates'].astype('datetime64[D]'); lat=z['lat']; lon=z['lon']
ii=z['ii']; jj=z['jj']
pydates=[dt.date(*map(int,str(x).split('-'))) for x in dates]
cum=[0,31,59,90,120,151,181,212,243,273,304,334]  # nonleap days before month
def doy(t):
    if t.month==2 and t.day==29: return 60
    n=cum[t.month-1]+t.day
    if t.year%4==0 and (t.year%100!=0 or t.year%400==0) and t.month>2: n+=1
    return n
assert doy(dt.date(2000,3,1))==61 and doy(dt.date(1992,12,31))==366 and doy(dt.date(2001,12,31))==365
idx={t:k for k,t in enumerate(pydates)}
base=[dt.date(y,1,1)+dt.timedelta(k) for y in range(1992,2003) for k in range(0,(dt.date(y,12,31)-dt.date(y,1,1)).days+1)]
base=[b for b in base if b<=dt.date(2002,12,31)]
anch={}
for b in base:
    anch.setdefault(doy(b),[]).append(b)
thr=np.full((367,)+S.shape[1:],np.nan); clim=np.full_like(thr,np.nan)
for dd in range(1,367):
    if dd==60: continue
    pool=set()
    for b in anch.get(dd,[]):
        for k in range(-5,6): pool.add(b+dt.timedelta(k))
    ix=sorted(idx[t] for t in pool)  # all in req range
    V=S[ix]
    with np.errstate(all='ignore'):
        thr[dd]=np.nanquantile(V,0.9,axis=0,method='hazen')
        clim[dd]=np.nanmean(V,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    a=a[1:367]  # 366 array index 0..365 for doy 1..366
    out=np.empty_like(a)
    for k in range(366):
        ids=[(k+o)%366 for o in range(-15,16)]
        out[k]=np.mean(a[ids],axis=0)
    return out
thr366=smooth(thr); clim366=smooth(clim)
# target
tstart=dt.date(2014,6,1); tend=dt.date(2014,8,31)
tdays=[dt.date(2014,6,1)+dt.timedelta(k) for k in range((tend-tstart).days+1)]
tix=[idx[t] for t in tdays]
T=S[tix]
sea=np.all(np.isfinite(T),axis=0)
print('sea cells',sea.sum(),'of',sea.size)
doys=np.array([doy(t) for t in tdays])
TH=thr366[doys-1]  # (n,60,60)
hot=(T>=TH)&sea[None]
nT=len(tdays)
mhw=np.zeros_like(hot)
for i in range(60):
    for j in range(60):
        if not sea[i,j]: continue
        h=hot[:,i,j]
        # candidate runs >=5
        runs=[]; k=0
        while k<nT:
            if h[k]:
                s=k
                while k<nT and h[k]: k+=1
                if k-s>=5: runs.append([s,k-1])
            else: k+=1
        if not runs: continue
        merged=[runs[0]]
        for s,e in runs[1:]:
            ps,pe=merged[-1]
            if s-pe-1<=2: merged[-1]=[ps,e]
            else: merged.append([s,e])
        for s,e in merged: mhw[s:e+1,i,j]=True
active=mhw.any(axis=(1,2))
events=[]; k=0
while k<nT:
    if active[k]:
        s=k
        while k<nT and active[k]: k+=1
        events.append((tdays[s],tdays[k-1]))
    else: k+=1
print('events',[(a.isoformat(),b.isoformat()) for a,b in events])
print('mhw cell-days',mhw.sum(),'active days',active.sum())
print('sea cells with nan thr on target:', int(np.sum(sea & np.isnan(TH).any(axis=0))))
os.makedirs('/tmp/out',exist_ok=True)
os.makedirs('output',exist_ok=True)
lat32=lat.astype(np.float32); lon32=lon.astype(np.float32)
# use exact dataset coords from file
import xarray as xr
x=xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc',engine='h5netcdf')
latc=x.latitude.values[ii]; lonc=x.longitude.values[jj]; x.close()
ds_out=xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype(np.uint8))},
    coords={'time':np.array(tdays,dtype='datetime64[ns]'),'lat':latc,'lon':lonc})
ds_out['mhw'].encoding={'zlib':True}
ds_out.to_netcdf('output/mhw_mask.nc')
rep={'region':{'lat_min':54.17,'lat_max':55.37,'lon_min':13.25,'lon_max':14.45},
     'baseline_analysed':{'start':'1992-01-01','end':'2002-12-31'},
     'target_analysed':{'start':'2014-06-01','end':'2014-08-31'},
     'events':[{'onset':a.isoformat(),'end':b.isoformat()} for a,b in events],
     'complete':True,
     'caveats':''}
json.dump(rep,open('output/report.json','w'),indent=2)
print(json.dumps(rep)[:1500])
'''
open('/tmp/an.py','w').write(code)
r=subprocess.run("cd /tmp && python an.py",shell=True,capture_output=True,text=True); print(r.stdout[-6000:], r.stderr[-3000:])