import pandas as pd,numpy as np,xarray as xr,json,os
z=np.load('/work/a.npz');B=z['B'].astype('f8');T=z['T'].astype('f8');lat=z['lat'];lon=z['lon']
bd=pd.date_range('1991-12-27','2003-01-05')
def doy(d): 
    return (pd.Timestamp(2000,d.month,d.day).dayofyear)
bdoy=np.array([doy(d) for d in bd])
sea=np.isfinite(T).all(0);print(sea.sum())
core=np.where((bd>='1992-01-01')&(bd<='2002-12-31'))[0]
thr=np.full((366,60,60),np.nan);clim=thr.copy()
for d in range(1,367):
    if d==60:continue
    idx=set()
    for i in core:
        if bdoy[i]==d: idx.update(range(max(0,i-5),min(len(bd),i+6)))
    P=B[sorted(idx)]
    thr[d-1]=np.nanquantile(P,0.9,axis=0,method='hazen');clim[d-1]=np.nanmean(P,0)
for a in (thr,clim): a[59]=(a[58]+a[60])/2
def sm(a): return np.mean([np.roll(a,-k,axis=0) for k in range(-15,16)],axis=0)
thr=sm(thr)
td=pd.date_range('2004-06-01','2004-08-31');tdoy=np.array([doy(d) for d in td])
hot=(T>=thr[tdoy-1])&sea
mhw=np.zeros(hot.shape,bool)
for i in range(60):
  for j in range(60):
    if not sea[i,j]:continue
    h=hot[:,i,j];n=len(h);runs=[];k=0
    while k<n:
        if h[k]:
            s=k
            while k<n and h[k]:k+=1
            if k-s>=5:runs.append([s,k-1])
        else:k+=1
    m=[]
    for r in runs:
        if m and r[0]-m[-1][1]-1<=2:m[-1][1]=r[1]
        else:m.append(r)
    for s,e in m:mhw[s:e+1,i,j]=True
act=mhw.any((1,2));ev=[];k=0
while k<len(act):
    if act[k]:
        s=k
        while k<len(act) and act[k]:k+=1
        ev.append({"onset":f"{td[s]:%Y-%m-%d}","end":f"{td[k-1]:%Y-%m-%d}"})
    else:k+=1
print(ev,mhw.sum())
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype('uint8'))},coords={'time':td,'lat':lat,'lon':lon}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":54.13,"lat_max":55.33,"lon_min":14.67,"lon_max":15.87},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2004-06-01","end":"2004-08-31"},"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))