
import pandas as pd, json, os
b=xr.open_dataarray('/work/b.nc').load();g=xr.open_dataarray('/work/g.nc').load()
def doy(ti):
    ti=pd.DatetimeIndex(ti); return np.where(ti.is_leap_year,ti.dayofyear,ti.dayofyear+(ti.month>2))
tb=pd.DatetimeIndex(b.time.values);V=b.values.astype(np.float64)
dd=doy(tb)
cen=[i for i,t in enumerate(tb) if t>=pd.Timestamp('1992-01-01') and t<=pd.Timestamp('2002-12-31')]
ny,nx=V.shape[1:]
thr=np.full((366,ny,nx),np.nan);clim=thr.copy()
for k in range(1,367):
    if k==60: continue
    idx=sorted({j for i in cen if dd[i]==k for j in range(i-5,i+6)})
    P=V[idx]
    thr[k-1]=np.nanquantile(P,0.9,axis=0,method='hazen');clim[k-1]=np.nanmean(P,axis=0)
for a in (thr,clim): a[59]=(a[58]+a[60])/2
def sm(a):
    return sum(np.roll(a,-o,axis=0) for o in range(-15,16))/31
thr=sm(thr)
G=g.values.astype(np.float64)
sea=np.isfinite(G).all(0)
hot=(G>=thr[doy(g.time.values)-1])&sea
T=hot.shape[0];m=np.zeros_like(hot)
for y in range(ny):
  for x in range(nx):
    if not sea[y,x]:continue
    h=hot[:,y,x];runs=[];i=0
    while i<T:
        if h[i]:
            j=i
            while j<T and h[j]:j+=1
            if j-i>=5:runs.append([i,j])
            i=j
        else:i+=1
    mer=[]
    for r in runs:
        if mer and r[0]-mer[-1][1]<=2:mer[-1][1]=r[1]
        else:mer.append(r)
    for a,c in mer:m[a:c,y,x]=1
act=m.any((1,2));ev=[];i=0
tt=pd.DatetimeIndex(g.time.values)
while i<T:
    if act[i]:
        j=i
        while j<T and act[j]:j+=1
        ev.append({"onset":str(tt[i].date()),"end":str(tt[j-1].date())});i=j
    else:i+=1
print(sea.sum(),ev)
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),m.astype('uint8'))},coords={'time':g.time.values,'lat':g.latitude.values,'lon':g.longitude.values}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":56.13,"lat_max":57.33,"lon_min":17.71,"lon_max":18.91},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2019-06-01","end":"2019-08-31"},"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))
