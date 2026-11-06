B=np.stack(B);T=np.stack(T)
def doy(ts): return np.array([ (pd.Timestamp(2000,t.month,t.day).dayofyear) for t in ts])
bdoy=doy(bd)
sea=np.isfinite(T).all(0);print(sea.sum())
core=[i for i,t in enumerate(bd) if t.year>=1992 and t.year<=2002]
thr=np.full((366,)+sea.shape,np.nan);clim=thr.copy()
for dd in range(1,367):
    if dd==60: continue
    idx=set()
    for i in core:
        if bdoy[i]==dd: idx.update(range(i-5,i+6))
    idx=sorted(j for j in idx if 0<=j<len(bd))
    P=B[idx][:,sea]
    thr[dd-1][sea]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim[dd-1][sea]=np.nanmean(P,axis=0)
for a in (thr,clim):
    a[59]=(a[58]+a[60])/2
def sm(a):
    return np.mean([np.roll(a,-k,axis=0) for k in range(-15,16)],axis=0)
thr=sm(thr)
tdoy=doy(td)
hot=(T>=thr[tdoy-1])&sea
def runs(h,minlen):
    out=np.zeros_like(h)
    for i in range(h.shape[1]):
        for j in range(h.shape[2]):
            if not sea[i,j]: continue
            x=h[:,i,j];n=len(x);k=0
            while k<n:
                if x[k]:
                    e=k
                    while e<n and x[e]: e+=1
                    if e-k>=minlen: out[k:e,i,j]=1
                    k=e
                else:k+=1
    return out
m=runs(hot,5).astype(bool)
# join gaps 1-2
for i in range(60):
  for j in range(60):
    x=m[:,i,j]
    if not x.any(): continue
    k=0;n=len(x)
    while k<n:
        if not x[k]:
            e=k
            while e<n and not x[e]: e+=1
            if k>0 and e<n and e-k<=2: x[k:e]=True
            k=e
        else:k+=1
act=m.any((1,2))
ev=[];s=None
for i,a in enumerate(act):
    if a and s is None:s=i
    if (not a) and s is not None: ev.append((s,i-1));s=None
if s is not None: ev.append((s,len(act)-1))
evs=[{"onset":str(td[a].date()),"end":str(td[b].date())} for a,b in ev];print(evs)
import json
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),m.astype('uint8'))},coords={'time':td,'lat':lat[li],'lon':lon[lo]}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":54.17,"lat_max":55.37,"lon_min":13.25,"lon_max":14.45},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2004-06-01","end":"2004-08-31"},"events":evs,"complete":True,"caveats":"Baseline windows included 1991-12-27..2003-01-05 as specified."},open('output/report.json','w'))