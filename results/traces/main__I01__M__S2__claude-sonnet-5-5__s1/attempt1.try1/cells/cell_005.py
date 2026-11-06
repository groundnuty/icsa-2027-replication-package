T=pd.DatetimeIndex(s.time.values);X=s.values.astype(np.float64)
def doy(ix):
    m=ix.month.values;d=ix.day.values
    cum=np.array([0,31,60,91,121,152,182,213,244,274,305,335])
    return cum[m-1]+d
bd=pd.date_range("1992-01-01","2002-12-31");bdoy=doy(bd)
pos={t:i for i,t in enumerate(T)}
thr=np.full((366,60,60),np.nan);clim=thr.copy()
for d in range(1,367):
    if d==60: continue
    idx=set()
    for b in bd[bdoy==d]:
        for k in range(-5,6):
            idx.add(pos[b+pd.Timedelta(days=k)])
    P=X[sorted(idx)]
    thr[d-1]=np.nanquantile(P,0.9,axis=0,method="hazen");clim[d-1]=np.nanmean(P,0)
for a in(thr,clim): a[59]=(a[58]+a[60])/2
def sm(a):
    return np.mean([np.roll(a,-k,axis=0) for k in range(-15,16)],axis=0)
thr=sm(thr)
tt=pd.DatetimeIndex(tg.time.values);Y=tg.values.astype(np.float64)
sea=np.isfinite(Y).all(0)
hot=(Y>=thr[doy(tt)-1])&sea
n=len(tt);mh=np.zeros_like(hot)
for i in range(60):
  for j in range(60):
    if not sea[i,j]: continue
    h=hot[:,i,j];runs=[];k=0
    while k<n:
        if h[k]:
            e=k
            while e+1<n and h[e+1]:e+=1
            if e-k+1>=5:runs.append([k,e])
            k=e+1
        else:k+=1
    mg=[]
    for r in runs:
        if mg and r[0]-mg[-1][1]-1<=2: mg[-1][1]=r[1]
        else: mg.append(r)
    for a,b in mg: mh[a:b+1,i,j]=True
act=mh.any((1,2));ev=[];k=0
while k<n:
    if act[k]:
        e=k
        while e+1<n and act[e+1]:e+=1
        ev.append({"onset":str(tt[k].date()),"end":str(tt[e].date())});k=e+1
    else:k+=1
print(sea.sum(),ev)
os.makedirs("output",exist_ok=True)
xr.Dataset({"mhw":(("time","lat","lon"),mh.astype(np.uint8))},coords={"time":tg.time.values,"lat":tg.latitude.values,"lon":tg.longitude.values}).to_netcdf("output/mhw_mask.nc")
json.dump({"region":{"lat_min":54.13,"lat_max":55.33,"lon_min":14.67,"lon_max":15.87},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2008-06-01","end":"2008-08-31"},"events":ev,"complete":True,"caveats":""},open("output/report.json","w"))