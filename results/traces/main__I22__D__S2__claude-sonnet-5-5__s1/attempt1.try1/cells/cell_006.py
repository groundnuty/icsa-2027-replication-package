
import xarray as xr,numpy as np,pandas as pd,json,os
s=xr.open_dataset('/work/sub.nc').analysed_sst
v=s.values.astype('float64'); t=pd.DatetimeIndex(s.time.values)
cum=np.array([0,31,60,91,121,152,182,213,244,274,305,335])
doy=cum[t.month-1]+t.day
idx0=np.where((t>='1992-01-01')&(t<='2002-12-31'))[0]
thr=np.full((367,)+v.shape[1:],np.nan)
for k in range(1,367):
    if k==60: continue
    ii=[i for i in idx0 if doy[i]==k]
    sel=np.unique(np.concatenate([np.arange(i-5,i+6) for i in ii]))
    thr[k]=np.nanquantile(v[sel],0.9,axis=0,method='hazen')
a=thr[1:].copy(); a[59]=(a[58]+a[60])/2
thr=np.mean([np.roll(a,-j,axis=0) for j in range(-15,16)],axis=0)
ti=np.where((t>='2004-06-01')&(t<='2004-08-31'))[0]
x=v[ti]; sea=np.isfinite(x).all(0)
hot=(x>=thr[doy[ti]-1])&sea
T=len(ti);m=np.zeros(hot.shape,bool)
for a_ in range(60):
  for b in range(60):
    if not sea[a_,b]: continue
    h=hot[:,a_,b];runs=[];i=0
    while i<T:
        if h[i]:
            j=i
            while j<T and h[j]: j+=1
            if j-i>=5: runs.append([i,j])
            i=j
        else:i+=1
    mg=[]
    for r in runs:
        if mg and r[0]-mg[-1][1]<=2: mg[-1][1]=r[1]
        else: mg.append(r)
    for r in mg: m[r[0]:r[1],a_,b]=1
act=m.any((1,2));ev=[];i=0
td=t[ti]
while i<T:
    if act[i]:
        j=i
        while j<T and act[j]: j+=1
        ev.append({"onset":str(td[i].date()),"end":str(td[j-1].date())});i=j
    else:i+=1
print(ev,sea.sum())
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),m.astype('uint8'))},coords={'time':td,'lat':s.latitude.values,'lon':s.longitude.values}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":57.41,"lat_max":58.61,"lon_min":18.69,"lon_max":19.89},
"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
"target_analysed":{"start":"2004-06-01","end":"2004-08-31"},
"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))
