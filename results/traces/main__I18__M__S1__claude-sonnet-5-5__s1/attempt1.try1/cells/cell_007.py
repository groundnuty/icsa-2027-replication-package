import numpy as np,pandas as pd,json,xarray as xr,os
A=np.load('/tmp/A.npy');T=np.load('/tmp/T.npy');lat,lon=np.load('/tmp/ll.npy',allow_pickle=True)
lat=lat.astype(float);lon=lon.astype(float)
li=np.where((lat>=57.13-1e-4)&(lat<=58.33+1e-4))[0];lo=np.where((lon>=22.79-1e-4)&(lon<=23.99+1e-4))[0]
print(lat[li][[0,-1]],lon[lo][[0,-1]])
A=A[:,li][:,:,lo];T=T[:,li][:,:,lo];lat=lat[li];lon=lon[lo]
sea=np.isfinite(T).all(0);print(sea.sum())
dates=pd.date_range('1991-12-27','2003-01-05')
def doy(ix):
    leap=ix.is_leap_year
    return np.array(ix.dayofyear)+((~leap)&(ix.month>2))
dd=doy(dates)
base=np.where((dates>='1992-01-01')&(dates<='2002-12-31'))[0]
thr=np.full((366,)+sea.shape,np.nan);clim=thr.copy()
for d_ in range(1,367):
    if d_==60:continue
    idx=set()
    for b in base:
        if dd[b]==d_: idx.update(range(b-5,b+6))
    idx=sorted(i for i in idx if 0<=i<len(dates))
    P=A[idx][:,sea]
    t=np.full(sea.shape,np.nan);c=t.copy()
    t[sea]=np.nanquantile(P,0.9,axis=0,method='hazen');c[sea]=np.nanmean(P,0)
    thr[d_-1]=t;clim[d_-1]=c
for a in(thr,clim):
    a[59]=(a[58]+a[60])/2
def sm(a): return sum(np.roll(a,k,axis=0) for k in range(-15,16))/31
thr=sm(thr)
td=doy(pd.DatetimeIndex(pd.date_range('2010-06-01','2010-08-31')))
hot=(T>=thr[td-1])&sea
nt=len(td);mhw=np.zeros(hot.shape,bool)
for i in range(hot.shape[1]):
  for j in range(hot.shape[2]):
    h=hot[:,i,j]
    if not h.any():continue
    runs=[];s=None
    for t in range(nt+1):
        if t<nt and h[t]:
            if s is None:s=t
        elif s is not None:
            if t-s>=5:runs.append([s,t-1])
            s=None
    m=[]
    for r in runs:
        if m and r[0]-m[-1][1]-1<=2:m[-1][1]=r[1]
        else:m.append(r)
    for a,b in m:mhw[a:b+1,i,j]=True
act=mhw.any((1,2));tx=pd.date_range('2010-06-01','2010-08-31')
ev=[];s=None
for t in range(nt+1):
    if t<nt and act[t]:
        if s is None:s=t
    elif s is not None:ev.append({"onset":f"{tx[s]:%Y-%m-%d}","end":f"{tx[t-1]:%Y-%m-%d}"});s=None
print(ev)
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype('uint8'))},coords={'time':tx,'lat':lat,'lon':lon}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":57.13,"lat_max":58.33,"lon_min":22.79,"lon_max":23.99},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2010-06-01","end":"2010-08-31"},"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))