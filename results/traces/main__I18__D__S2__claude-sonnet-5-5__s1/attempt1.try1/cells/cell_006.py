
import json,os,numpy as np,pandas as pd,xarray as xr
ds=xr.open_dataset('/work/s.nc',engine='h5netcdf')
la=ds.latitude.values;lo=ds.longitude.values
li=np.where((la>=57.13-1e-4)&(la<=58.33+1e-4))[0];oi=np.where((lo>=22.79-1e-4)&(lo<=23.99+1e-4))[0]
B=np.load('/work/B.npy');T=np.load('/work/T.npy')
bt=pd.date_range('1991-12-27','2003-01-05')
def doy(d): 
    return np.array([ (pd.Timestamp(2000,x.month,x.day).dayofyear) for x in d])
bd=doy(bt)
base=np.where((bt>='1992-01-01')&(bt<='2002-12-31'))[0]
thr=np.full((366,60,60),np.nan)
for d in range(1,367):
    if d==60: continue
    idx=set()
    for i in base:
        if bd[i]==d: idx.update(range(i-5,i+6))
    thr[d-1]=np.nanquantile(B[sorted(idx)],0.9,axis=0,method='hazen')
thr[59]=(thr[58]+thr[60])/2
thr=sum(np.roll(thr,-k,axis=0) for k in range(-15,16))/31
tt=pd.date_range('2010-06-01','2010-08-31');td=doy(tt)
sea=np.isfinite(T).all(0);print(sea.sum())
hot=(T>=thr[td-1])&sea
mhw=np.zeros_like(hot);n=len(tt)
for i in range(60):
  for j in range(60):
    if not sea[i,j]: continue
    h=hot[:,i,j];runs=[];k=0
    while k<n:
        if h[k]:
            m=k
            while m<n and h[m]:m+=1
            if m-k>=5:runs.append([k,m])
            k=m
        else:k+=1
    mg=[]
    for r in runs:
        if mg and r[0]-mg[-1][1]<=2: mg[-1][1]=r[1]
        else: mg.append(r)
    for a,b in mg: mhw[a:b,i,j]=True
act=mhw.any((1,2));ev=[];k=0
while k<n:
    if act[k]:
        m=k
        while m<n and act[m]:m+=1
        ev.append({"onset":str(tt[k].date()),"end":str(tt[m-1].date())});k=m
    else:k+=1
print(ev)
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype('uint8'))},coords={'time':tt,'lat':la[li],'lon':lo[oi]}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":57.13,"lat_max":58.33,"lon_min":22.79,"lon_max":23.99},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2010-06-01","end":"2010-08-31"},"events":ev,"complete":True,"caveats":"Baseline pools also include 1991-12-27..31 and 2003-01-01..05 per method. Grid cells lat 57.14-58.32, lon 22.80-23.98."},open('output/report.json','w'))
