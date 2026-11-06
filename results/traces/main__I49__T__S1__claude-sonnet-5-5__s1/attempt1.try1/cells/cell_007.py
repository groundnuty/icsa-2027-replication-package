import pickle,numpy as np,datetime as dt,json,os,xarray as xr
days,res=pickle.load(open('/tmp/r.pkl','rb'))
lat=res[0][1];lon=res[0][2]
A=np.stack([r[0] for r in res]).astype('float64')  # note float32->64
nb=(dt.date(2003,1,5)-dt.date(1991,12,27)).days+1
B=A[:nb];T=A[nb:]
print(np.nanmin(T),np.nanmax(T),np.isnan(B).mean())
sea=np.isfinite(T).all(0);print(sea.sum())
def doy(d):
    return (dt.date(2000,d.month,d.day)-dt.date(2000,1,1)).days+1
bd=days[:nb]
dd=np.array([doy(d) for d in bd])
# baseline dates: 1992-01-01..2002-12-31
idx_by={}
for i,d in enumerate(bd): idx_by[d]=i
base=[d for d in bd if dt.date(1992,1,1)<=d<=dt.date(2002,12,31)]
thr=np.full((366,)+sea.shape,np.nan);clim=thr.copy()
for k in range(1,367):
    if k==60: continue
    ids=set()
    for d in base:
        if doy(d)==k:
            for o in range(-5,6):
                ids.add(idx_by[d+dt.timedelta(o)])
    pool=B[sorted(ids)]
    thr[k-1]=np.nanquantile(pool,0.9,axis=0,method='hazen')
    clim[k-1]=np.nanmean(pool,axis=0)
for a in (thr,clim): a[59]=(a[58]+a[60])/2
def sm(a):
    return sum(np.roll(a,-s,axis=0) for s in range(-15,16))/31
thr=sm(thr)
td=[d for d in days[nb:]]
tt=np.array([doy(d) for d in td])
hot=(T>=thr[tt-1])&sea
# per-cell runs
n=len(td);mhw=np.zeros_like(hot)
def runs(x):
    r=[];i=0
    while i<len(x):
        if x[i]:
            j=i
            while j<len(x) and x[j]:j+=1
            r.append((i,j));i=j
        else:i+=1
    return r
for a in range(hot.shape[1]):
  for b in range(hot.shape[2]):
    if not sea[a,b]:continue
    rs=[r for r in runs(hot[:,a,b]) if r[1]-r[0]>=5]
    m=[]
    for r in rs:
        if m and r[0]-m[-1][1]<=2: m[-1]=(m[-1][0],r[1])
        else: m.append(r)
    for s,e in m: mhw[s:e,a,b]=True
act=mhw.any((1,2));ev=[]
for i in range(n):
    if act[i]:
        if i==0 or not act[i-1]: s=i
        if i==n-1 or not act[i+1]: ev.append({"onset":str(td[s]),"end":str(td[i])})
print(ev,mhw.sum())
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype('uint8'))},coords={'time':np.array(td,dtype='datetime64[ns]'),'lat':lat,'lon':lon}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":64.51,"lat_max":65.71,"lon_min":21.97,"lon_max":23.17},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2019-06-01","end":"2019-08-31"},"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))