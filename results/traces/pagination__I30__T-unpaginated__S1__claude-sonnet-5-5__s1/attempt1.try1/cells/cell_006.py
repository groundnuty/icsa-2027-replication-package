A=np.load('/tmp/A.npy');lat=np.load('/tmp/lat.npy');lon=np.load('/tmp/lon.npy')
nb=len(base);B=A[:nb];T=A[nb:]
doy=lambda dt:(np.array([ (pd.Timestamp(2000,m,dd).dayofyear) for m,dd in zip(dt.month,dt.day)]))
bd=doy(base); isb=(base>='1992-01-01')&(base<='2002-12-31')
sea=np.isfinite(T).all(0);print(sea.sum())
thr=np.full((366,60,60),np.nan);clim=thr.copy()
for d in range(1,367):
    if d==60: continue
    idx=np.where(isb&(bd==d))[0]
    w=np.unique(np.concatenate([np.arange(i-5,i+6) for i in idx]));w=w[(w>=0)&(w<nb)]
    P=B[w]
    thr[d-1]=np.nanquantile(P,0.9,axis=0,method='hazen');clim[d-1]=np.nanmean(P,axis=0)
for a in(thr,clim): a[59]=(a[58]+a[60])/2
def sm(a):
    return sum(np.roll(a,s,axis=0) for s in range(-15,16))/31
thr=sm(thr)
td=doy(tgt)
hot=(T>=thr[td-1])&sea
nt=len(tgt);mhw=np.zeros_like(hot)
for i in range(60):
  for j in range(60):
    if not sea[i,j]: continue
    h=hot[:,i,j];runs=[];k=0
    while k<nt:
        if h[k]:
            e=k
            while e+1<nt and h[e+1]:e+=1
            if e-k+1>=5: runs.append([k,e])
            k=e+1
        else:k+=1
    m=[]
    for r_ in runs:
        if m and r_[0]-m[-1][1]-1<=2: m[-1][1]=r_[1]
        else:m.append(r_)
    for s,e in m: mhw[s:e+1,i,j]=1
act=mhw.any((1,2));ev=[];k=0
while k<nt:
    if act[k]:
        e=k
        while e+1<nt and act[e+1]:e+=1
        ev.append({"onset":f"{tgt[k]:%Y-%m-%d}","end":f"{tgt[e]:%Y-%m-%d}"});k=e+1
    else:k+=1
print(ev,mhw.sum())
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype('uint8'))},coords={'time':tgt,'lat':lat,'lon':lon}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":58.69,"lat_max":59.89,"lon_min":18.69,"lon_max":19.89},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2010-06-01","end":"2010-08-31"},"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))