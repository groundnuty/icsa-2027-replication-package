import xarray as xr,numpy as np,pandas as pd,json,os
s=xr.open_dataset('/work/b.nc').analysed_sst;tg=xr.open_dataset('/work/t.nc').analysed_sst
X=s.values.astype('float64');T=pd.DatetimeIndex(s.time.values)
def doy(ix):
    m=ix.month.values;dd=ix.day.values
    cum=np.array([0,31,60,91,121,152,182,213,244,274,305,335])
    return cum[m-1]+dd
D=doy(T)
base=np.where((T>='1992-01-01')&(T<='2002-12-31'))[0]
ny,nx=X.shape[1:]
thr=np.full((366,ny,nx),np.nan);clim=thr.copy()
for k in range(1,367):
    if k==60: continue
    idx=sorted({j for i in base[D[base]==k] for j in range(i-5,i+6)})
    P=X[idx]
    thr[k-1]=np.nanquantile(P,0.9,axis=0,method='hazen');clim[k-1]=np.nanmean(P,axis=0)
for A in(thr,clim): A[59]=(A[58]+A[60])/2
def sm(A):
    return np.mean([np.roll(A,-o,axis=0) for o in range(-15,16)],axis=0)
thr=sm(thr)
Y=tg.values.astype('float64');TT=pd.DatetimeIndex(tg.time.values);DT=doy(TT)
sea=np.isfinite(Y).all(0)
hot=(Y>=thr[DT-1])&sea
n=len(TT);m=np.zeros_like(hot)
for i in range(ny):
  for j in range(nx):
    if not sea[i,j]: continue
    h=hot[:,i,j];runs=[];k=0
    while k<n:
        if h[k]:
            e=k
            while e+1<n and h[e+1]:e+=1
            if e-k+1>=5: runs.append([k,e])
            k=e+1
        else:k+=1
    mg=[]
    for r in runs:
        if mg and r[0]-mg[-1][1]-1<=2: mg[-1][1]=r[1]
        else: mg.append(r)
    for a,b in mg:m[a:b+1,i,j]=1
act=m.any((1,2));ev=[];k=0
while k<n:
    if act[k]:
        e=k
        while e+1<n and act[e+1]:e+=1
        ev.append({"onset":str(TT[k].date()),"end":str(TT[e].date())});k=e+1
    else:k+=1
print(sea.sum(),ev)
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),m.astype('uint8'))},coords={'time':tg.time.values,'lat':tg.latitude.values,'lon':tg.longitude.values}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":58.69,"lat_max":59.89,"lon_min":18.69,"lon_max":19.89},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2010-06-01","end":"2010-08-31"},"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))