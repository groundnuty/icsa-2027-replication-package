
import xarray as xr,numpy as np,pandas as pd, json, os
s=xr.open_dataarray('/work/reg.nc');t=pd.DatetimeIndex(s.time.values);V=s.values.astype('float64')
doy=lambda ix: np.array([ (pd.Timestamp(2000,m,dd).dayofyear) for m,dd in zip(ix.month,ix.day)])
tt=doy(t)
bidx=np.where((t>='1992-01-01')&(t<='2002-12-31'))[0]
ny,nx=V.shape[1:]
thr=np.full((366,ny,nx),np.nan)
for dd in range(1,367):
    if dd==60: continue
    idx=set()
    for b in bidx[tt[bidx]==dd]:
        idx.update(range(b-5,b+6))
    idx=sorted(idx);P=V[idx]
    thr[dd-1]=np.nanquantile(P,0.9,axis=0,method='hazen')
thr[59]=(thr[58]+thr[60])/2
thr=sum(np.roll(thr,-k,axis=0) for k in range(-15,16))/31
ti=np.where((t>='2008-06-01')&(t<='2008-08-31'))[0]
X=V[ti];sea=np.isfinite(X).all(0)
hot=(X>=thr[tt[ti]-1])&sea
T=len(ti);m=np.zeros(hot.shape,bool)
for i in range(ny):
  for j in range(nx):
    if not sea[i,j]:continue
    h=hot[:,i,j];runs=[];k=0
    while k<T:
        if h[k]:
            e=k
            while e<T and h[e]:e+=1
            if e-k>=5:runs.append([k,e])
            k=e
        else:k+=1
    mer=[]
    for r in runs:
        if mer and r[0]-mer[-1][1]<=2:mer[-1][1]=r[1]
        else:mer.append(r)
    for a,b in mer:m[a:b,i,j]=1
act=m.any((1,2));ev=[];k=0
tg=t[ti]
while k<T:
    if act[k]:
        e=k
        while e+1<T and act[e+1]:e+=1
        ev.append({"onset":str(tg[k].date()),"end":str(tg[e].date())});k=e+1
    else:k+=1
print(sea.sum(),ev)
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),m.astype('uint8'))},coords={'time':tg,'lat':s.latitude.values,'lon':s.longitude.values}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":57.83,"lat_max":59.03,"lon_min":17.41,"lon_max":18.61},
"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
"target_analysed":{"start":"2008-06-01","end":"2008-08-31"},"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))
