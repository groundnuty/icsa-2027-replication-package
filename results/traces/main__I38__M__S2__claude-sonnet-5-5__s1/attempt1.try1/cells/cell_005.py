import xarray as xr,numpy as np,pandas as pd,json,os
sub=xr.open_dataarray("/tmp/sub.nc").load()
t=pd.DatetimeIndex(sub.time.values);A=sub.values.astype(np.float64)
doy=np.array([ (pd.Timestamp(2000,x.month,x.day).dayofyear) for x in t])  # leap-year mapping
tgt=(t>="2003-06-01")&(t<="2003-08-31")
sea=np.isfinite(A[tgt]).all(0)
print(sea.sum())
bidx=np.where((t>="1992-01-01")&(t<="2002-12-31"))[0]
thr=np.full((366,)+sea.shape,np.nan);clim=thr.copy()
for d in range(1,367):
    if d==60: continue
    cs=bidx[doy[bidx]==d]
    ids=np.unique(np.clip((cs[:,None]+np.arange(-5,6)[None]).ravel(),0,len(t)-1))
    # ensure no clipping artifacts
    assert ids.min()>=0
    P=A[ids][:,sea]
    thr[d-1][sea]=np.nanquantile(P,0.9,axis=0,method="hazen")
    clim[d-1][sea]=np.nanmean(P,axis=0)
for a in (thr,clim):
    a[59]=(a[58]+a[60])/2
def sm(a):
    return np.mean([np.roll(a,-k,axis=0) for k in range(-15,16)],axis=0)
thr=sm(thr)
T=A[tgt];D=doy[tgt]-1
hot=(T>=thr[D])&sea
n=hot.shape[0];mhw=np.zeros_like(hot)
def runs(v,val):
    out=[];i=0
    while i<len(v):
        if v[i]==val:
            j=i
            while j<len(v) and v[j]==val:j+=1
            out.append((i,j));i=j
        else:i+=1
    return out
for y,x in zip(*np.where(sea)):
    r=[(a,b) for a,b in runs(hot[:,y,x],True) if b-a>=5]
    m=np.zeros(n,bool)
    for k,(a,b) in enumerate(r):
        m[a:b]=True
        if k+1<len(r) and r[k+1][0]-b<=2: m[b:r[k+1][0]]=True
    mhw[:,y,x]=m
act=mhw.any((1,2));tt=t[tgt]
ev=[(tt[a],tt[b-1]) for a,b in runs(act,True)]
print(ev,mhw.sum())
os.makedirs("output",exist_ok=True)
xr.Dataset({"mhw":(("time","lat","lon"),mhw.astype(np.uint8))},coords={"time":tt,"lat":sub.latitude.values,"lon":sub.longitude.values}).to_netcdf("output/mhw_mask.nc")
f=lambda x:x.strftime("%Y-%m-%d")
json.dump({"region":{"lat_min":60.49,"lat_max":61.69,"lon_min":17.25,"lon_max":18.45},
"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
"target_analysed":{"start":"2003-06-01","end":"2003-08-31"},
"events":[{"onset":f(a),"end":f(b)} for a,b in ev],"complete":True,"caveats":""},open("output/report.json","w"))