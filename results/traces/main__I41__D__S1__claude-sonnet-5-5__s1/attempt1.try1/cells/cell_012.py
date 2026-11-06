import numpy as np,pandas as pd,json,os,xarray as xr
A=np.load('/work/A.npy');lat,lon=np.load('/work/ll.npy',allow_pickle=True)
ext=pd.date_range('1991-12-27','2003-01-05');n=len(ext)
B=A[:n];T=A[n:]
def doy(ix): 
    return np.array([ (pd.Timestamp(2000,x.month,x.day).dayofyear) for x in ix])
dd=doy(ext)
bidx=np.where((ext>=pd.Timestamp('1992-01-01'))&(ext<=pd.Timestamp('2002-12-31')))[0]
thr=np.full((366,60,60),np.nan);clim=thr.copy()
for d in range(1,367):
    if d==60: continue
    ids=[]
    for i in bidx:
        if dd[i]==d: ids+=list(range(i-5,i+6))
    P=B[ids]
    thr[d-1]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim[d-1]=np.nanmean(P,axis=0)
for a in (thr,clim): a[59]=(a[58]+a[60])/2
def sm(a):
    return np.mean([np.roll(a,-k,axis=0) for k in range(-15,16)],axis=0)
thr=sm(thr)
tt=pd.date_range('2021-06-01','2021-08-31')
sea=np.isfinite(T).all(0)
td=doy(tt)
hot=(T>=thr[td-1])&sea
nt=len(tt);mhw=np.zeros_like(hot)
for i in range(60):
  for j in range(60):
    if not sea[i,j]: continue
    h=hot[:,i,j];runs=[];s=None
    for k in range(nt+1):
        if k<nt and h[k]:
            if s is None:s=k
        elif s is not None:
            runs.append([s,k-1]);s=None
    runs=[r for r in runs if r[1]-r[0]+1>=5]
    merged=[]
    for r in runs:
        if merged and r[0]-merged[-1][1]-1<=2: merged[-1][1]=r[1]
        else: merged.append(r)
    for a,b in merged: mhw[a:b+1,i,j]=True
act=mhw.any(axis=(1,2))
ev=[];s=None
for k in range(nt+1):
    if k<nt and act[k]:
        if s is None:s=k
    elif s is not None: ev.append({"onset":f"{tt[s]:%Y-%m-%d}","end":f"{tt[k-1]:%Y-%m-%d}"});s=None
print(sea.sum(),ev,mhw.sum())
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype('uint8'))},coords={'time':tt,'lat':lat,'lon':lon}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":61.57,"lat_max":62.77,"lon_min":20.17,"lon_max":21.37},
"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2021-06-01","end":"2021-08-31"},
"events":ev,"complete":True,"caveats":""},open('output/report.json','w'),indent=1)