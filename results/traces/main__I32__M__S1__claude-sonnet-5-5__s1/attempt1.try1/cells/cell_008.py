import pickle,numpy as np,pandas as pd,os,json,xarray as xr
dates,R=pickle.load(open('/tmp/r.pkl','rb'))
la,lo=R[0][1],R[0][2]
S=np.stack([r[0] for r in R])[:,1:-1,1:-1];la=la[1:-1];lo=lo[1:-1]
def doy(t): 
    t=pd.DatetimeIndex(t);return np.array([ (pd.Timestamp(2000,m,dd).dayofyear) for m,dd in zip(t.month,t.day)])
nb=(dates<='2003-01-05').sum();B=S[:nb];bd=dates[:nb]
tg=S[nb:];td=dates[nb:]
bdoy=doy(bd);idx={t:i for i,t in enumerate(bd)}
sea=np.isfinite(tg).all(0);print(sea.sum())
thr=np.full((366,)+B.shape[1:],np.nan)
for k in range(1,367):
    if k==60:continue
    ii=set()
    for t in bd[(bdoy==k)&(bd>='1992-01-01')&(bd<='2002-12-31')]:
        for o in range(-5,6):
            u=t+pd.Timedelta(days=o)
            if u in idx:ii.add(idx[u])
    P=B[sorted(ii)]
    thr[k-1]=np.nanquantile(P,0.9,axis=0,method='hazen')
thr[59]=(thr[58]+thr[60])/2
thr=sum(np.roll(thr,-s,axis=0) for s in range(-15,16))/31
tdoy=doy(td)
hot=(tg>=thr[tdoy-1])&sea
mh=np.zeros_like(hot)
def runs(v):
    r=[];i=0
    while i<len(v):
        if v[i]:
            j=i
            while j<len(v) and v[j]:j+=1
            r.append((i,j));i=j
        else:i+=1
    return r
for y in range(hot.shape[1]):
    for x in range(hot.shape[2]):
        if not sea[y,x]:continue
        rr=[r for r in runs(hot[:,y,x]) if r[1]-r[0]>=5]
        for a,b in zip(rr,rr[1:]):
            if b[0]-a[1]<=2: mh[a[1]:b[0],y,x]=True
        for a,b in rr: mh[a:b,y,x]=True
act=mh.any((1,2));ev=[(a,b-1) for a,b in runs(act)]
evs=[{"onset":f"{td[a]:%Y-%m-%d}","end":f"{td[b]:%Y-%m-%d}"} for a,b in ev];print(evs,sea.sum(),mh.sum())
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),mh.astype('uint8'))},coords={'time':td,'lat':la,'lon':lo}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":59.05,"lat_max":60.25,"lon_min":21.25,"lon_max":22.45},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2005-06-01","end":"2005-08-31"},"events":evs,"complete":True,"caveats":"Grid is offset 0.02 deg so cells 59.06-60.24N, 21.26-22.44E (60x60) are inside bounds."},open('output/report.json','w'))