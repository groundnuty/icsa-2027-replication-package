import numpy as np,pandas as pd,json,os
A=np.load('/tmp/A.npy');lat,lon=np.load('/tmp/ll.npy',allow_pickle=True)
lat=lat.astype(np.float32);lon=lon.astype(np.float32)
bd=pd.date_range('1991-12-27','2003-01-05');nb=len(bd)
tdts=pd.date_range('2014-06-01','2014-08-31')
B=A[:nb];T=A[nb:]
cum=np.cumsum([0,31,29,31,30,31,30,31,31,30,31,30])
doy=lambda idx:cum[idx.month-1]+idx.day
bdoy=np.array(doy(bd));tdoy=np.array(doy(tdts))
base_idx=np.where((bd>='1992-01-01')&(bd<='2002-12-31'))[0]
sea=np.isfinite(T).all(0);print(sea.sum())
thr=np.full((366,)+sea.shape,np.nan);clim=thr.copy()
for d in range(1,367):
    if d==60:continue
    ids=set()
    for i in base_idx:
        if bdoy[i]==d: ids.update(range(i-5,i+6))
    ids=sorted(i for i in ids if 0<=i<nb)
    P=B[ids]
    thr[d-1]=np.nanquantile(P,0.9,axis=0,method='hazen');clim[d-1]=np.nanmean(P,axis=0)
for a in(thr,clim): a[59]=(a[58]+a[60])/2
def sm(a):
    return np.mean([np.roll(a,-k,axis=0) for k in range(-15,16)],axis=0)
thr=sm(thr)
hot=T>=thr[tdoy-1]
hot&=sea
nt=len(tdts);m=np.zeros_like(hot)
def runs(v,val):
    out=[];s=None
    for i,x in enumerate(list(v)+[not val]):
        if x==val and s is None:s=i
        if x!=val and s is not None:out.append((s,i-1));s=None
    return out
for i in range(60):
  for j in range(60):
    if not sea[i,j]:continue
    r=[q for q in runs(hot[:,i,j],True) if q[1]-q[0]+1>=5]
    mm=np.zeros(nt,bool)
    for k,(s,e) in enumerate(r):
        mm[s:e+1]=True
        if k>0 and 1<=s-r[k-1][1]-1<=2: mm[r[k-1][1]:s+1]=True
    m[:,i,j]=mm
act=m.any((1,2));ev=[(s,e) for s,e in runs(act,True)]
print(ev,m.sum())
import xarray as xr
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),m.astype(np.uint8))},coords={'time':tdts,'lat':lat,'lon':lon}).to_netcdf('output/mhw_mask.nc')
f=lambda i:str(tdts[i].date())
json.dump({"region":{"lat_min":54.17,"lat_max":55.37,"lon_min":13.25,"lon_max":14.45},
"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
"target_analysed":{"start":"2014-06-01","end":"2014-08-31"},
"events":[{"onset":f(s),"end":f(e)} for s,e in ev],"complete":True,"caveats":""},open('output/report.json','w'))