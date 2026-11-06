def doy(d):
    d=pd.DatetimeIndex(d);return np.array([(pd.Timestamp(2000,m,dd).dayofyear) for m,dd in zip(d.month,d.day)])
D=doy(bt);idx={d:i for i,d in enumerate(bt)}
isb=(bt>=pd.Timestamp("1992-01-01"))&(bt<=pd.Timestamp("2002-12-31"))
ny=base.shape[1:]
thr=np.full((366,)+ny,np.nan);clim=thr.copy()
for d in range(1,367):
    if d==60: continue
    ii=set()
    for c in np.where(isb&(D==d))[0]:
        for o in range(-5,6):
            j=c+o
            if 0<=j<len(bt): ii.add(j)
    pool=base[sorted(ii)]
    thr[d-1]=np.nanquantile(pool,0.9,axis=0,method="hazen");clim[d-1]=np.nanmean(pool,axis=0)
for a in(thr,clim): a[59]=(a[58]+a[60])/2
def sm(a):
    return sum(np.roll(a,-k,axis=0) for k in range(-15,16))/31
thr=sm(thr)
tv=tg.values.astype("float64");sea=np.isfinite(tv).all(0)
Dt=doy(tg.time.values)
hot=(tv>=thr[Dt-1])&sea
T=hot.shape[0];mh=np.zeros_like(hot)
for i in range(hot.shape[1]):
  for j in range(hot.shape[2]):
    if not sea[i,j]: continue
    h=hot[:,i,j];runs=[];k=0
    while k<T:
        if h[k]:
            e=k
            while e<T and h[e]:e+=1
            if e-k>=5:runs.append([k,e])
            k=e
        else:k+=1
    m=[]
    for r in runs:
        if m and r[0]-m[-1][1]<=2:m[-1][1]=r[1]
        else:m.append(r)
    for a,b in m:mh[a:b,i,j]=True
act=mh.any((1,2));ev=[];k=0
while k<T:
    if act[k]:
        e=k
        while e<T and act[e]:e+=1
        ev.append({"onset":str(tg.time.values[k])[:10],"end":str(tg.time.values[e-1])[:10]});k=e
    else:k+=1
print(sea.sum(),ev)
import os,json
os.makedirs("output",exist_ok=True)
xr.Dataset({"mhw":(("time","lat","lon"),mh.astype("uint8"))},coords={"time":tg.time.values,"lat":la[li],"lon":lo[oi]}).to_netcdf("output/mhw_mask.nc")
json.dump({"region":{"lat_min":64.51,"lat_max":65.71,"lon_min":21.97,"lon_max":23.17},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2019-06-01","end":"2019-08-31"},"events":ev,"complete":True,"caveats":"Baseline windows used 1991-12-27..2003-01-05 as specified."},open("output/report.json","w"))