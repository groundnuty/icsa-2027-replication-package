import numpy as np,pickle,datetime as dt,json,os
days,A,lat,lon=pickle.load(open('/tmp/d.pkl','rb'))
idx={d:i for i,d in enumerate(days)}
def doy(d):
    return (dt.date(2000,d.month,d.day)-dt.date(2000,1,1)).days+1
base=[d for d in days if dt.date(1992,1,1)<=d<=dt.date(2002,12,31)]
nb=len(base)
thr=np.full((366,60,60),np.nan);clim=thr.copy()
for dd in range(1,367):
    if dd==60: continue
    ii=[]
    for b in base:
        if doy(b)==dd:
            for k in range(-5,6):
                ii.append(idx[b+dt.timedelta(k)])
    pool=A[ii]  # duplicates? windows overlap across years? no, years differ
    thr[dd-1]=np.nanquantile(pool,0.9,axis=0,method='hazen')
    clim[dd-1]=np.nanmean(pool,axis=0)
for a in (thr,clim): a[59]=(a[58]+a[60])/2
def sm(a):
    return sum(np.roll(a,-k,axis=0) for k in range(-15,16))/31
thr=sm(thr)
tdays=rng=[d for d in days if d>=dt.date(2021,6,1)]
T=np.array([idx[d] for d in tdays]);S=A[T]
sea=np.isfinite(S).all(0)
print(sea.sum())
th=np.stack([thr[doy(d)-1] for d in tdays])
hot=(S>=th)&sea
nt=len(tdays);mhw=np.zeros_like(hot)
for i in range(60):
  for j in range(60):
    if not sea[i,j]:continue
    h=hot[:,i,j];runs=[];k=0
    while k<nt:
        if h[k]:
            e=k
            while e+1<nt and h[e+1]:e+=1
            if e-k+1>=5:runs.append([k,e])
            k=e+1
        else:k+=1
    m=[]
    for r in runs:
        if m and r[0]-m[-1][1]-1<=2:m[-1][1]=r[1]
        else:m.append(r)
    for a,b in m:mhw[a:b+1,i,j]=1
act=mhw.any((1,2));ev=[];k=0
while k<nt:
    if act[k]:
        e=k
        while e+1<nt and act[e+1]:e+=1
        ev.append({"onset":str(tdays[k]),"end":str(tdays[e])});k=e+1
    else:k+=1
print(ev,mhw.sum())
import xarray as xr
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype('uint8'))},coords={'time':np.array(tdays,dtype='datetime64[ns]'),'lat':lat,'lon':lon}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":57.33,"lat_max":58.53,"lon_min":9.03,"lon_max":10.23},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2021-06-01","end":"2021-08-31"},"events":ev,"complete":True,"caveats":"Directory listing truncated at 1000 files; fetched files by name. Baseline windows used 1991-12-27..2003-01-05."},open('output/report.json','w'))