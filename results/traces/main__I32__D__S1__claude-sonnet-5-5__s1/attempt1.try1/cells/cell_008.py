import numpy as np,xarray as xr,datetime as dt,json,os
def days(a,b):
    d=a
    while d<=b: yield d; d+=dt.timedelta(1)
def load(ds_):
    out=[]
    for d in ds_:
        x=xr.open_dataset(d.strftime('/work/d/sst_%Y%m%d.nc'),engine='h5netcdf')
        x=x.sel(latitude=slice(59.05-1e-4,60.25+1e-4),longitude=slice(21.25-1e-4,22.45+1e-4))
        out.append(x.analysed_sst.values[0].astype('float64')); lat,lon=x.latitude.values,x.longitude.values
    return np.array(out),lat,lon
bd=list(days(dt.date(1991,12,27),dt.date(2003,1,5)))
B,lat,lon=load(bd);T,_,_=load(list(days(dt.date(2005,6,1),dt.date(2005,8,31))))
print(B.shape,T.shape,lat,lon,np.nanmean(T),np.isnan(B).mean())
def doy(d): return (dt.date(2000,d.month,d.day)-dt.date(2000,1,1)).days+1
sea=np.isfinite(T).all(0);print(sea.sum())
bdoy=np.array([doy(d) for d in bd]);bidx=np.arange(len(bd))
inb=np.array([dt.date(1992,1,1)<=d<=dt.date(2002,12,31) for d in bd])
ny,nx=sea.shape
thr=np.full((366,ny,nx),np.nan);clim=thr.copy()
for k in range(1,367):
    if k==60: continue
    ci=bidx[inb&(bdoy==k)]
    sel=set()
    for c in ci:
        for o in range(-5,6):
            if 0<=c+o<len(bd): sel.add(c+o)
    pool=B[sorted(sel)]
    thr[k-1]=np.nanquantile(pool,0.9,axis=0,method='hazen');clim[k-1]=np.nanmean(pool,0)
for a in(thr,clim): a[59]=(a[58]+a[60])/2
def sm(a): return np.mean([np.roll(a,-s,0) for s in range(-15,16)],0)
thr=sm(thr)
Tdoy=np.array([doy(d) for d in days(dt.date(2005,6,1),dt.date(2005,8,31))])
hot=(T>=thr[Tdoy-1])&sea
nt=len(Tdoy);mhw=np.zeros(hot.shape,bool)
for i in range(ny):
  for j in range(nx):
    if not sea[i,j]: continue
    h=hot[:,i,j].copy();runs=[];t=0
    while t<nt:
        if h[t]:
            s=t
            while t<nt and h[t]:t+=1
            if t-s>=5:runs.append([s,t-1])
        else:t+=1
    m=[]
    for r in runs:
        if m and r[0]-m[-1][1]-1<=2:m[-1][1]=r[1]
        else:m.append(r)
    for s,e in m:mhw[s:e+1,i,j]=True
act=mhw.any((1,2));ev=[];t=0;D=list(days(dt.date(2005,6,1),dt.date(2005,8,31)))
while t<nt:
    if act[t]:
        s=t
        while t<nt and act[t]:t+=1
        ev.append({"onset":str(D[s]),"end":str(D[t-1])})
    else:t+=1
print(ev,mhw.sum())
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype('uint8'))},coords={'time':np.array(D,dtype='datetime64[ns]'),'lat':lat,'lon':lon}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":59.05,"lat_max":60.25,"lon_min":21.25,"lon_max":22.45},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2005-06-01","end":"2005-08-31"},"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))