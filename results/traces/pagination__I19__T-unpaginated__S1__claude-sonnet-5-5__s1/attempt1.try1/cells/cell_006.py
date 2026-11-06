import numpy as np,pandas as pd,xarray as xr,json,os
a=np.load('/tmp/a.npy');lat=np.load('/tmp/lat.npy');lon=np.load('/tmp/lon.npy')
la=slice(1,-1);lo=slice(1,-1)
a=a[:,1:-1,1:-1];lat=lat[1:-1];lon=lon[1:-1]
print(lat[[0,-1]],lon[[0,-1]],a.shape)
d=pd.date_range('1991-12-27','2003-01-05');nb=len(d)
tg=a[nb:];base=a[:nb]
sea=np.isfinite(tg).all(0)
doy=lambda x:np.where((x.month>2)|((x.month==2)&(x.day==29)),0,0)  # unused
def mdoy(ix):
    return np.array([ (pd.Timestamp(2000,m,dd).dayofyear) for m,dd in zip(ix.month,ix.day)])
bd=mdoy(d)
bidx=[i for i,x in enumerate(d) if '1992-01-01'<=str(x.date())<='2002-12-31']
thr=np.full((366,)+sea.shape,np.nan);clim=thr.copy()
for D in range(1,367):
    if D==60:continue
    ids=set()
    for i in bidx:
        if bd[i]==D: ids.update(range(i-5,i+6))
    ids=sorted(j for j in ids if 0<=j<nb)
    pool=base[ids]
    thr[D-1]=np.nanquantile(pool,0.9,axis=0,method='hazen')
    clim[D-1]=np.nanmean(pool,0)
for A in(thr,clim): A[59]=(A[58]+A[60])/2
def sm(A):
    return sum(np.roll(A,s,axis=0) for s in range(-15,16))/31
thr=sm(thr)
td=mdoy(t)-1
hot=tg>=thr[td]
hot&=sea
T=len(t)
def runs(h):
    out=np.zeros_like(h)
    for i in range(h.shape[1]):
        for j in range(h.shape[2]):
            x=h[:,i,j];k=0;segs=[]
            while k<T:
                if x[k]:
                    e=k
                    while e<T and x[e]:e+=1
                    if e-k>=5:segs.append([k,e])
                    k=e
                else:k+=1
            m=[]
            for s in segs:
                if m and s[0]-m[-1][1]<=2:m[-1][1]=s[1]
                else:m.append(s)
            for s,e in m:out[s:e,i,j]=True
    return out
mhw=runs(hot)
act=mhw.any((1,2))
ev=[];k=0
while k<T:
    if act[k]:
        e=k
        while e+1<T and act[e+1]:e+=1
        ev.append({"onset":str(t[k].date()),"end":str(t[e].date())});k=e+1
    else:k+=1
print(sea.sum(),ev)
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype('uint8'))},coords={'time':t,'lat':lat,'lon':lon}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":57.13,"lat_max":58.33,"lon_min":22.79,"lon_max":23.99},
"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2014-06-01","end":"2014-08-31"},
"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))