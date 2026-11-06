
code = r'''
import numpy as np, pickle, datetime as dt, json, os, warnings
import xarray as xr
warnings.filterwarnings('ignore')
dates,arr,lat,lon=pickle.load(open('/tmp/sst.pkl','rb'))
idx={d:i for i,d in enumerate(dates)}
latm=(lat>=60.49)&(lat<=61.69); lonm=(lon>=17.25)&(lon<=18.45)
sub=arr[:,latm][:,:,lonm]; LAT=lat[latm]; LON=lon[lonm]
ny=sub.shape[1]; nx=sub.shape[2]
mdays=[31,29,31,30,31,30,31,31,30,31,30,31]
doy_of={}; off=0
for m,L in enumerate(mdays,1):
    for dd in range(1,L+1): doy_of[(m,dd)]=off+dd
    off+=L
def doy(d): return doy_of[(d.month,d.day)]
base=[d for d in dates if dt.date(1992,1,1)<=d<=dt.date(2002,12,31)]
tgt=[d for d in dates if dt.date(2010,6,1)<=d<=dt.date(2010,8,31)]
tidx=[idx[d] for d in tgt]
finite_all=np.all(np.isfinite(sub[tidx]),axis=0)
print('sea cells', finite_all.sum(), 'ny nx', ny, nx, 'ntarget', len(tgt), 'nbase', len(base))
thr=np.full((367,ny,nx),np.nan); clim=np.full((367,ny,nx),np.nan)
pools={}
for d in base:
    k=doy(d)
    if k==60: continue
    pools.setdefault(k,set())
    for o in range(-5,6):
        t=d+dt.timedelta(o)
        if t in idx: pools[k].add(idx[t])
for k in range(1,367):
    if k==60: continue
    x=sub[sorted(pools[k])]
    thr[k]=np.nanquantile(x,0.9,axis=0,method='hazen')
    clim[k]=np.nanmean(x,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    a=a[1:367]; out=np.empty_like(a)
    for i in range(366):
        ids=[(i+j)%366 for j in range(-15,16)]
        out[i]=np.mean(a[ids],axis=0)
    return out
T=smooth(thr)
nt=len(tgt)
tdoy=np.array([doy(d) for d in tgt])
Tt=T[tdoy-1]
S=sub[tidx]
hot=(S>=Tt)&finite_all[None]
mhw=np.zeros((nt,ny,nx),bool)
for iy in range(ny):
    for ix in range(nx):
        if not finite_all[iy,ix]: continue
        h=hot[:,iy,ix]
        runs=[]; t=0
        while t<nt:
            if h[t]:
                s=t
                while t<nt and h[t]: t+=1
                if t-s>=5: runs.append([s,t-1])
            else: t+=1
        merged=[]
        for r in runs:
            gap=r[0]-merged[-1][1]-1 if merged else None
            if merged and 1<=gap<=2: merged[-1][1]=r[1]
            else: merged.append(list(r))
        for s,e in merged: mhw[s:e+1,iy,ix]=True
active=mhw.any(axis=(1,2))
events=[]; t=0
while t<nt:
    if active[t]:
        s=t
        while t<nt and active[t]: t+=1
        events.append({"onset":tgt[s].isoformat(),"end":tgt[t-1].isoformat()})
    else: t+=1
print('mhw cell-days', mhw.sum(), 'active days', active.sum())
print('events', events)
print('hot cell-days', hot.sum())
os.makedirs('output',exist_ok=True)
ds=xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype(np.uint8))},
    coords={'time':np.array(tgt,dtype='datetime64[ns]'),'lat':LAT,'lon':LON})
ds['mhw'].attrs={'long_name':'marine heatwave mask'}
ds.to_netcdf('output/mhw_mask.nc', encoding={'mhw':{'dtype':'uint8','zlib':True}})
rep={"region":{"lat_min":60.49,"lat_max":61.69,"lon_min":17.25,"lon_max":18.45},
 "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
 "target_analysed":{"start":"2010-06-01","end":"2010-08-31"},
 "events":events,"complete":True,
 "caveats":"Grid cells in region: 60x60 (lat 60.50-61.68, lon 17.26-18.44). Threshold/climatology use baseline pools with +/-5 day windows extended into 1991-12-27..2003-01-05. Sea cells: finite on all target days (3293 of 3600). Land cells are 0 in mask."}
json.dump(rep,open('output/report.json','w'),indent=2)
print(open('output/report.json').read())
'''
open('/tmp/mhw.py','w').write(code)
import subprocess
print(subprocess.run(['python','/tmp/mhw.py'],capture_output=True,text=True,cwd='/tmp').stdout[-4000:])
