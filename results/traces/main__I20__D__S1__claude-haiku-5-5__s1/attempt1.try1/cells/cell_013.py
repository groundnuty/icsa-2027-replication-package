code = r'''
import numpy as np, datetime as dt, json, os, warnings
warnings.filterwarnings('ignore')
import xarray as xr
c=np.load('/work/s/coords.npz'); LAT=c['lat']; LON=c['lon']
start=dt.date(1991,12,27); end=dt.date(2012,8,31)
days=[start+dt.timedelta(i) for i in range((end-start).days+1)]
N=len(days)
S=np.empty((N,LAT.size,LON.size))
for i,d in enumerate(days):
    S[i]=np.load(f'/work/s/sub/{d:%Y%m%d}.npz')['sst']
idx={d:i for i,d in enumerate(days)}
def doy(d):
    return (d.replace(year=2000)-dt.date(2000,1,1)).days+1
tgt=[dt.date(2012,6,1)+dt.timedelta(i) for i in range(92)]
ti=[idx[d] for d in tgt]
T=S[ti]
sea=np.all(np.isfinite(T),axis=0)
thr=np.full((367,)+sea.shape,np.nan); clim=np.full((367,)+sea.shape,np.nan)
for d in range(1,367):
    if d==60: continue
    md=dt.date(2000,1,1)+dt.timedelta(d-1)
    vals=[]
    for Y in range(1992,2003):
        b=dt.date(Y,md.month,md.day)
        for k in range(-5,6):
            vals.append(S[idx[b+dt.timedelta(k)]])
    P=np.stack(vals)
    thr[d]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim[d]=np.nanmean(P,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    a=a[1:367]
    out=np.empty_like(a)
    for i in range(366):
        ks=[(i+k)%366 for k in range(-15,16)]
        out[i]=np.mean(a[ks],axis=0)
    return out
thrS=smooth(thr); climS=smooth(clim)
doys=np.array([doy(d) for d in tgt])
H=np.zeros((92,)+sea.shape,bool)
for t in range(92):
    H[t]=(T[t]>=thrS[doys[t]-1])&sea
def runs(b):
    r=[];i=0;n=len(b)
    while i<n:
        if b[i]:
            j=i
            while j+1<n and b[j+1]: j+=1
            r.append((i,j)); i=j+1
        else: i+=1
    return r
M=np.zeros_like(H)
ny,nx=sea.shape
for y in range(ny):
    for x in range(nx):
        if not sea[y,x]: continue
        rs=[r for r in runs(H[:,y,x]) if r[1]-r[0]+1>=5]
        if not rs: continue
        merged=[list(rs[0])]
        for s,e in rs[1:]:
            if s-merged[-1][1]-1<=2: merged[-1][1]=e
            else: merged.append([s,e])
        for s,e in merged: M[s:e+1,y,x]=True
active=M.any(axis=(1,2))
ev=[{"onset":str(tgt[s]),"end":str(tgt[e])} for s,e in runs(active)]
print('sea',sea.sum(),'hot cell-days',H.sum(),'MHW cell-days', M.sum(), 'active days', active.sum())
print(ev)
os.makedirs('/work/output',exist_ok=True)
ds=xr.Dataset({'mhw':(('time','lat','lon'),M.astype(np.uint8))},
  coords={'time':(('time'),np.array([np.datetime64(d) for d in tgt],dtype='datetime64[ns]')),
          'lat':('lat',LAT),'lon':('lon',LON)})
ds['mhw'].attrs={'long_name':'marine heatwave flag'}
ds.to_netcdf('/work/output/mhw_mask.nc',engine='netcdf4' if True else 'h5netcdf',encoding={'mhw':{'dtype':'uint8','zlib':True}})
rep={"region":{"lat_min":57.33,"lat_max":58.53,"lon_min":9.03,"lon_max":10.23},
 "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
 "target_analysed":{"start":"2012-06-01","end":"2012-08-31"},
 "events":ev,"complete":True,
 "caveats":"Baseline/threshold pools use 1992-2002 with edge days 1991-12-27..31 and 2003-01-01..05. Region grid cells 57.34-58.52N, 9.04-10.22E (60x60 cells, all inside bounds). Only cells finite on all target days are treated as sea; others set to 0. Climatology computed but not used for detection. SST taken from daily files as stored (kelvin)."}
json.dump(rep,open('/work/output/report.json','w'),indent=2)
print(open('/work/output/report.json').read()[:300])
'''
open('/work/run.py','w').write(code)
exec(compile(code,'run','exec'))