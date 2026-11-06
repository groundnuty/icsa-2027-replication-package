import pickle,numpy as np,pandas as pd,json,os,xarray as xr
days,arrs,lat,lon=pickle.load(open('/tmp/d.pkl','rb'))
days=pd.DatetimeIndex(days);X=np.stack(arrs).astype(np.float64)
bmask=days<='2003-01-05'
bd=days[bmask];B=X[bmask]
tm=days>='2021-06-01';T=X[tm];td=days[tm]
def doy(ix):
    return np.array([ (pd.Timestamp(2000,m,dd).dayofyear) for m,dd in zip(ix.month,ix.day)])
bdoy=doy(bd)
inb=(bd>='1992-01-01')&(bd<='2002-12-31')
thr=np.full((366,)+B.shape[1:],np.nan);clim=thr.copy()
for d in range(1,367):
    if d==60: continue
    ci=np.where(inb&(bdoy==d))[0]
    sel=set()
    for c in ci: sel.update(range(max(0,c-5),min(len(bd),c+6)))
    pool=B[sorted(sel)]
    thr[d-1]=np.nanquantile(pool,0.9,axis=0,method='hazen')
    clim[d-1]=np.nanmean(pool,axis=0)
for a in (thr,clim): a[59]=(a[58]+a[60])/2
def sm(a):
    return sum(np.roll(a,-k,axis=0) for k in range(-15,16))/31
thr=sm(thr)
sea=np.isfinite(T).all(0)
tdoy=doy(td)
hot=(T>=thr[tdoy-1])&sea
nt=len(td);mhw=np.zeros_like(hot)
for i in range(hot.shape[1]):
  for j in range(hot.shape[2]):
    h=hot[:,i,j]
    if not h.any(): continue
    runs=[];s=None
    for t in range(nt+1):
        v=t<nt and h[t]
        if v and s is None:s=t
        if not v and s is not None:
            if t-s>=5:runs.append([s,t-1])
            s=None
    mer=[]
    for r in runs:
        if mer and r[0]-mer[-1][1]-1<=2: mer[-1][1]=r[1]
        else: mer.append(r)
    for a,b in mer: mhw[a:b+1,i,j]=True
act=mhw.any((1,2));ev=[];s=None
for t in range(nt+1):
    v=t<nt and act[t]
    if v and s is None:s=t
    if not v and s is not None: ev.append({"onset":str(td[s].date()),"end":str(td[t-1].date())});s=None
print(sea.sum(),mhw.sum(),ev)
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype(np.uint8))},coords={'time':td,'lat':lat,'lon':lon}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":54.45,"lat_max":55.65,"lon_min":16.05,"lon_max":17.25},
"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2021-06-01","end":"2021-08-31"},
"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))