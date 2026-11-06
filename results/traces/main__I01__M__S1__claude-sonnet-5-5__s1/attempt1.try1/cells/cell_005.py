def doy(ix): return np.array([pd.Timestamp(2000,t.month,t.day).dayofyear for t in ix])
bdoy=doy(bd)
base=np.where((bd>='1992-01-01')&(bd<='2002-12-31'))[0]
thr=np.full((366,60,60),np.nan);clim=thr.copy()
for k in range(1,367):
    if k==60: continue
    c=base[bdoy[base]==k]
    idx=np.unique(np.concatenate([c+o for o in range(-5,6)]));idx=idx[(idx>=0)&(idx<len(bd))]
    P=B[idx]
    thr[k-1]=np.nanquantile(P,0.9,axis=0,method='hazen');clim[k-1]=np.nanmean(P,axis=0)
for a in(thr,clim): a[59]=(a[58]+a[60])/2
def sm(a): return np.mean([np.roll(a,-s,axis=0) for s in range(-15,16)],axis=0)
thr=sm(thr)
sea=np.isfinite(T).all(0)
tdoy=doy(td)
hot=(T>=thr[tdoy-1])&sea
def runs(h):
    out=np.zeros_like(h);n=len(h);i=0
    while i<n:
        if h[i]:
            j=i
            while j<n and h[j]: j+=1
            yield i,j; i=j
        else:i+=1
M=np.zeros(hot.shape,bool)
for a in range(60):
  for b in range(60):
    if not sea[a,b]: continue
    rs=[(i,j) for i,j in runs(hot[:,a,b]) if j-i>=5]
    mg=[]
    for i,j in rs:
        if mg and i-mg[-1][1]<=2: mg[-1][1]=j
        else: mg.append([i,j])
    for i,j in mg: M[i:j,a,b]=True
act=M.any((1,2));ev=[]
for i,j in runs(act): ev.append({"onset":str(td[i].date()),"end":str(td[j-1].date())})
print(sea.sum(),ev)
import os,json
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),M.astype('uint8'))},coords={'time':td,'lat':lat[li],'lon':lon[lj]}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":54.13,"lat_max":55.33,"lon_min":14.67,"lon_max":15.87},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2008-06-01","end":"2008-08-31"},"events":ev,"complete":True,"caveats":"Baseline windows used 1991-12-27..2003-01-05 as specified."},open('output/report.json','w'))