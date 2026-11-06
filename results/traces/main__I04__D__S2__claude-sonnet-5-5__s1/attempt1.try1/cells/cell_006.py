
import xarray as xr,numpy as np,pandas as pd,os,json
ds=xr.open_dataset('/work/s.nc',engine='h5netcdf')
la=ds.latitude.values;lo=ds.longitude.values
li=np.where((la>=54.39-1e-4)&(la<=55.59+1e-4))[0];oi=np.where((lo>=18.25-1e-4)&(lo<=19.45+1e-4))[0]
X=xr.open_dataarray('/work/x.nc');tt=pd.DatetimeIndex(X.time.values);A=X.values.astype('f8')
D=np.array([pd.Timestamp(2000,x.month,x.day).dayofyear for x in tt])
tm=(tt>='2020-06-01')&(tt<='2020-08-31')
T=A[tm]; sea=np.isfinite(T).all(0)
bm=(tt<='2003-01-05')
Bt=tt[bm];BA=A[bm]
bidx={d:i for i,d in enumerate(Bt)}
thr=np.full((366,)+A.shape[1:],np.nan)
for d in range(1,367):
    if d==60: continue
    ds_=[x for x in Bt if D[bidx[x]]==d and '1992-01-01'<=str(x.date())<='2002-12-31']
    idx=set()
    for x in ds_:
        for k in range(-5,6):
            y=x+pd.Timedelta(days=k)
            if y in bidx: idx.add(bidx[y])
    P=BA[sorted(idx)]
    thr[d-1]=np.nanquantile(P,0.9,axis=0,method='hazen')
thr[59]=(thr[58]+thr[60])/2
thr=sum(np.roll(thr,-k,axis=0) for k in range(-15,16))/31
Dt=D[tm];H=(T>=thr[Dt-1])&sea
M=np.zeros(H.shape,bool)
def runs(v):
    r=[];i=0
    while i<len(v):
        if v[i]:
            j=i
            while j<len(v) and v[j]:j+=1
            r.append((i,j));i=j
        else:i+=1
    return r
for a in range(H.shape[1]):
  for b in range(H.shape[2]):
    if not sea[a,b]:continue
    r=[x for x in runs(H[:,a,b]) if x[1]-x[0]>=5]
    for k,(s,e) in enumerate(r):
        M[s:e,a,b]=1
        if k+1<len(r) and r[k+1][0]-e<=2: M[e:r[k+1][0],a,b]=1
act=M.any((1,2));dates=tt[tm];ev=[]
for s,e in runs(act): ev.append({"onset":str(dates[s].date()),"end":str(dates[e-1].date())})
print(sea.sum(),ev,len(dates))
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),M.astype('uint8'))},coords={'time':dates,'lat':la[li],'lon':lo[oi]}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":54.39,"lat_max":55.59,"lon_min":18.25,"lon_max":19.45},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2020-06-01","end":"2020-08-31"},"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))
