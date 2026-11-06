import numpy as np, datetime as dt, json, os
import xarray as xr
c=np.load('/tmp/cache.npz')
V=c['V']; LA=c['LA']; LO=c['LO']; dates=[dt.datetime.strptime(s,'%Y%m%d').date() for s in c['dates']]
start=dates[0]
def doy(d): return dt.date(2000,d.month,d.day).timetuple().tm_yday
base_lo,base_hi=dt.date(1992,1,1),dt.date(2002,12,31)
ndate=len(dates)
thr=np.full((367,60,60),np.nan); clim=np.full((367,60,60),np.nan)
bidx_by_doy={}
for b in [d for d in dates if base_lo<=d<=base_hi]:
    bidx_by_doy.setdefault(doy(b),[]).append(b)
for d in range(1,367):
    if d==60: continue
    idxs=set()
    for b in bidx_by_doy[d]:
        for k in range(-5,6):
            idxs.add((b+dt.timedelta(k)-start).days)
    idxs=sorted(i for i in idxs if 0<=i<ndate)
    pool=V[idxs]
    with np.errstate(all='ignore'):
        thr[d]=np.nanquantile(pool,0.9,axis=0,method='hazen')
thr[60]=(thr[59]+thr[61])/2
def smooth(a):
    a=a[1:367]; out=np.empty_like(a)
    for i in range(366):
        out[i]=a[[(i+k)%366 for k in range(-15,16)]].mean(axis=0)
    return out
thr_s=smooth(thr)
tidx=[i for i,d in enumerate(dates) if dt.date(2008,6,1)<=d<=dt.date(2008,8,31)]
tdates=[dates[i] for i in tidx]
T=V[tidx]
sea=np.all(np.isfinite(T),axis=0)
doys=np.array([doy(d) for d in tdates])
th=thr_s[doys-1]
with np.errstate(invalid='ignore'):
    hot=(T>=th)&sea[None]
def runs(b):
    out=[];n=len(b);i=0
    while i<n:
        if b[i]:
            j=i
            while j+1<n and b[j+1]: j+=1
            out.append((i,j)); i=j+1
        else: i+=1
    return out
mhw=np.zeros(hot.shape,bool)
for y in range(60):
    for x in range(60):
        if not sea[y,x]: continue
        segs=[s for s in runs(hot[:,y,x]) if s[1]-s[0]+1>=5]
        if not segs: continue
        merged=[list(segs[0])]
        for s in segs[1:]:
            if s[0]-merged[-1][1]-1<=2: merged[-1][1]=s[1]
            else: merged.append(list(s))
        for a,bb in merged: mhw[a:bb+1,y,x]=True
active=mhw.any(axis=(1,2))
events=[]; i=0; n=len(active)
while i<n:
    if active[i]:
        j=i
        while j+1<n and active[j+1]: j+=1
        events.append({"onset":tdates[i].isoformat(),"end":tdates[j].isoformat()}); i=j+1
    else: i+=1
print(events)
# output
ds=xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype(np.uint8))},
    coords={'time':np.array([np.datetime64(d.isoformat()) for d in tdates],dtype='datetime64[ns]'),
            'lat':LA,'lon':LO})
ds['mhw'].attrs={'long_name':'marine heatwave mask (1 = inside per-cell MHW)'}
os.makedirs('output',exist_ok=True)
ds.to_netcdf('output/mhw_mask.nc',encoding={'mhw':{'dtype':'uint8','zlib':True}})
report={"region":{"lat_min":57.83,"lat_max":59.03,"lon_min":17.41,"lon_max":18.61},
 "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
 "target_analysed":{"start":"2008-06-01","end":"2008-08-31"},
 "events":events,"complete":True,
 "caveats":"Region grid cells used: 60x60 at 57.84-59.02N, 17.42-18.60E (0.02 deg spacing). 3294 sea cells. First event starts on the first target day (2008-06-01), so its true onset may be earlier (left-censored by target period). Baseline pool windows used data from 1991-12-27 to 2003-01-05. Source files listed truncated (1000 entries) so files were opened by explicit path. Day 60 handled as mean of 59 and 61 for threshold; climatology not needed for output."}
json.dump(report,open('output/report.json','w'),indent=2)
print(open('output/report.json').read())
chk=xr.open_dataset('output/mhw_mask.nc'); print(chk.mhw.shape, chk.mhw.dtype, int(chk.mhw.sum()))