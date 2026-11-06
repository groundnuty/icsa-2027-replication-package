
s=xr.open_dataarray("/tmp/s.nc").load()
tt=pd.DatetimeIndex(s.time.values)
def doy(ix):
    m=ix.month.values;dd=ix.day.values
    cum=np.array([0,31,60,91,121,152,182,213,244,274,305,335])
    return cum[m-1]+dd
dy=doy(tt)
X=s.values.astype(np.float64)
bs=np.where((tt>="1992-01-01")&(tt<="2002-12-31"))[0]
thr=np.full((366,)+X.shape[1:],np.nan);clim=thr.copy()
for k in range(1,367):
    if k==60: continue
    cs=[i for i in bs if dy[i]==k]
    idx=sorted({j for i in cs for j in range(i-5,i+6)})
    pool=X[idx]
    thr[k-1]=np.nanquantile(pool,0.9,axis=0,method="hazen")
    clim[k-1]=np.nanmean(pool,axis=0)
for a in(thr,clim): a[59]=(a[58]+a[60])/2
def sm(a):
    return sum(np.roll(a,-o,axis=0) for o in range(-15,16))/31
thr=sm(thr)
tm=(tt>="2014-06-01")&(tt<="2014-08-31")
Y=X[tm];dt=tt[tm];dyt=dy[tm]
sea=np.isfinite(Y).all(0)
hot=(Y>=thr[dyt-1])&sea
T=len(Y);mh=np.zeros_like(hot)
def runs(v):
    r=[];i=0
    while i<len(v):
        if v[i]:
            j=i
            while j<len(v) and v[j]:j+=1
            r.append((i,j));i=j
        else:i+=1
    return r
for a in range(hot.shape[1]):
  for b in range(hot.shape[2]):
    if not sea[a,b]:continue
    rs=[r for r in runs(hot[:,a,b]) if r[1]-r[0]>=5]
    if not rs:continue
    m=np.zeros(T,bool);cur=list(rs[0])
    for r in rs[1:]:
        if r[0]-cur[1]<=2: cur[1]=r[1]
        else: m[cur[0]:cur[1]]=1;cur=list(r)
    m[cur[0]:cur[1]]=1
    mh[:,a,b]=m
act=mh.any((1,2));ev=[]
for i,j in runs(act): ev.append({"onset":str(dt[i].date()),"end":str(dt[j-1].date())})
print(sea.sum(),ev)
import os,json
os.makedirs("output",exist_ok=True)
xr.Dataset({"mhw":(("time","lat","lon"),mh.astype(np.uint8))},coords={"time":dt.values,"lat":la[iy],"lon":lo[ix]}).to_netcdf("output/mhw_mask.nc")
json.dump({"region":{"lat_min":54.17,"lat_max":55.37,"lon_min":13.25,"lon_max":14.45},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2014-06-01","end":"2014-08-31"},"events":ev,"complete":True,"caveats":""},open("output/report.json","w"))
