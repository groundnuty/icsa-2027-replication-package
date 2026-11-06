import numpy as np,pandas as pd,json,xarray as xr
z=np.load('output/cache.npz');A=z['A'];lat=z['lat'];lon=z['lon'];ds=pd.to_datetime(z['dates'])
print(np.nanmin(A),np.nanmax(A))
def doy(t): 
    return np.array([ (pd.Timestamp(2000,x.month,x.day).dayofyear) for x in t])  # 2000 leap
nb=(ds<='2003-01-05')
Ab=A[nb];db=ds[nb];dd=doy(db)
base=(db>='1992-01-01')&(db<='2002-12-31')
thr=np.full((366,60,60),np.nan);clim=thr.copy()
idx={t:i for i,t in enumerate(db)}
for d in range(1,367):
    if d==60: continue
    ii=set()
    for t in db[base&(dd==d)]:
        for k in range(-5,6):
            u=t+pd.Timedelta(days=k)
            if u in idx: ii.add(idx[u])
    pool=Ab[sorted(ii)]
    with np.errstate(all='ignore'):
        thr[d-1]=np.nanquantile(pool,0.9,axis=0,method='hazen');clim[d-1]=np.nanmean(pool,axis=0)
for a in (thr,clim): a[59]=(a[58]+a[60])/2
def sm(a):
    return np.mean([np.roll(a,-k,axis=0) for k in range(-15,16)],axis=0)
thr=sm(thr)
T=A[~nb];td=ds[~nb];print(len(td),td[0],td[-1])
sea=np.isfinite(T).all(0);print(sea.sum())
hot=(T>=thr[doy(td)-1])&sea
nt=len(td);mhw=np.zeros_like(hot)
def runs(v):
    out=[];i=0
    while i<len(v):
        if v[i]:
            j=i
            while j<len(v) and v[j]:j+=1
            out.append((i,j));i=j
        else:i+=1
    return out
for a in range(60):
    for b in range(60):
        if not sea[a,b]:continue
        r=[x for x in runs(hot[:,a,b]) if x[1]-x[0]>=5]
        m=np.zeros(nt,bool)
        for k,(s,e) in enumerate(r):
            m[s:e]=True
            if k+1<len(r) and r[k+1][0]-e<=2: m[e:r[k+1][0]]=True
        mhw[:,a,b]=m
act=mhw.any((1,2));ev=[(str(td[s].date()),str(td[e-1].date())) for s,e in runs(act)];print(ev,mhw.sum())
xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype('uint8'))},coords={'time':td,'lat':lat,'lon':lon}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":54.45,"lat_max":55.65,"lon_min":16.05,"lon_max":17.25},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2021-06-01","end":"2021-08-31"},"events":[{"onset":a,"end":b} for a,b in ev],"complete":True,"caveats":"Baseline pools also used 1991-12-27..31 and 2003-01-01..05 as specified."},open('output/report.json','w'))