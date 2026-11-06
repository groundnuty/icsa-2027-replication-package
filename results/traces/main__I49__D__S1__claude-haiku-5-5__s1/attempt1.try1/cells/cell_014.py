code = r'''
import numpy as np, datetime as dt, json, os
import xarray as xr
days=[]
x=dt.date(1991,12,27)
while x<=dt.date(2003,1,5): days.append(x); x+=dt.timedelta(1)
nb=len(days)
tgt=[]
x=dt.date(2019,6,1)
while x<=dt.date(2019,8,31): tgt.append(x); x+=dt.timedelta(1)
alld=days+tgt
idx={d:i for i,d in enumerate(alld)}
first=np.load('/work/c/'+alld[0].strftime('%Y%m%d')+'.npz')
lat=first['lat']; lon=first['lon']
S=np.empty((len(alld),)+first['sst'].shape,np.float64)
for i,d in enumerate(alld):
    z=np.load('/work/c/'+d.strftime('%Y%m%d')+'.npz')
    assert np.array_equal(z['lat'],lat) and np.array_equal(z['lon'],lon)
    S[i]=z['sst']
ti=[idx[d] for d in tgt]
T=S[ti]
sea=np.all(np.isfinite(T),axis=0)
print('sea cells',sea.sum())

def doy(d):
    if d.month==2 and d.day==29: return 60
    base=[0,31,60,91,121,152,182,213,244,274,305,335][d.month-1]
    return base+d.day
assert doy(dt.date(2001,2,28))==59 and doy(dt.date(2001,3,1))==61 and doy(dt.date(2001,12,31))==366 and doy(dt.date(2000,2,29))==60
bdates=[]
x=dt.date(1992,1,1)
while x<=dt.date(2002,12,31): bdates.append(x); x+=dt.timedelta(1)
pool_idx={d:[] for d in range(1,367)}
seen={d:set() for d in range(1,367)}
for b in bdates:
    d=doy(b)
    if d==60: continue
    for k in range(-5,6):
        xx=b+dt.timedelta(k)
        if xx not in seen[d]:
            seen[d].add(xx); pool_idx[d].append(idx[xx])
print('pool sizes', len(pool_idx[1]), len(pool_idx[366]), len(pool_idx[152]), len(pool_idx[60]))
thr=np.full((367,)+sea.shape,np.nan); clim=np.full_like(thr,np.nan)
for d in range(1,367):
    if d==60: continue
    P=S[pool_idx[d]]
    with np.errstate(all='ignore'):
        thr[d]=np.nanquantile(P,0.9,axis=0,method='hazen')
        clim[d]=np.nanmean(P,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    a=a[1:367]
    out=np.empty_like(a)
    for i in range(366):
        ids=[(i+k)%366 for k in range(-15,16)]
        out[i]=a[ids].mean(axis=0)
    return out
thrS=smooth(thr); climS=smooth(clim)
# thrS[i] corresponds to doy i+1
print('nan thr sea', np.isnan(thrS[:,sea]).sum())

# per-cell MHW on target days
Tdoy=np.array([doy(d) for d in tgt])
thr_t=thrS[Tdoy-1]            # ntgt, 60,60
hot=(T>=thr_t)&sea[None]
ntg,ny,nx=hot.shape
mhw=np.zeros_like(hot)
for r in range(ny):
    for c in range(nx):
        if not sea[r,c]: continue
        h=hot[:,r,c]
        # candidate runs >=5
        runs=[]; t=0
        while t<ntg:
            if h[t]:
                s=t
                while t<ntg and h[t]: t+=1
                if t-s>=5: runs.append([s,t-1])
            else: t+=1
        # join runs separated by 1 or 2 non-hot days
        merged=[]
        for rr in runs:
            if merged and (rr[0]-merged[-1][1]-1) in (1,2):
                merged[-1][1]=rr[1]
            else: merged.append(list(rr))
        for s,e in merged: mhw[s:e+1,r,c]=True
active=mhw.any(axis=(1,2))
events=[]
t=0
while t<ntg:
    if active[t]:
        s=t
        while t<ntg and active[t]: t+=1
        events.append({"onset":tgt[s].isoformat(),"end":tgt[t-1].isoformat()})
    else: t+=1
print('active days', active.sum(), 'events', events)
print('cells with any MHW', mhw.any(axis=0).sum(), 'mhw cell-days', mhw.sum())

os.makedirs('/work/output',exist_ok=True) if False else None
os.makedirs('output',exist_ok=True)
import netCDF4
ds=xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype(np.uint8))},
    coords={'time':np.array(tgt,dtype='datetime64[ns]'),'lat':lat,'lon':lon})
ds['mhw'].attrs={}
ds.to_netcdf('output/mhw_mask.nc', encoding={'mhw':{'dtype':'uint8','zlib':True}})
report={"region":{"lat_min":64.51,"lat_max":65.71,"lon_min":21.97,"lon_max":23.17},
 "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
 "target_analysed":{"start":"2019-06-01","end":"2019-08-31"},
 "events":events,"complete":True,
 "caveats":"Grid cells in the file are 64.52-65.70N, 21.98-23.16E (60x60 at 0.02 deg), the spec bounds used as region. Threshold/climatology pools include the extended edge dates (1991-12-27..31, 2003-01-01..05) as the method specifies. Non-sea cells (NaN in target period) are 0 in mask."}
json.dump(report,open('output/report.json','w'),indent=2)
print('written')
'''
open('/work/analysis.py','w').write(code)
import subprocess
r=subprocess.run('cd /work && python analysis.py',shell=True,capture_output=True,text=True)
print(r.stdout[-4000:], r.stderr[-3000:])