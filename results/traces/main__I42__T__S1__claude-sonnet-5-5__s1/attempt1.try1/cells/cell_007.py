import pickle,numpy as np,pandas as pd,json,xarray as xr
ok=pickle.load(open('/tmp/ok.pkl','rb'))
dates=pd.DatetimeIndex([d for d,_ in ok])
lat=ok[0][1].latitude.values.astype('float64');lon=ok[0][1].longitude.values
A=np.concatenate([r.analysed_sst.values for _,r in ok]).astype('float64')
print(A.shape,np.nanmin(A),np.nanmax(A),np.isnan(A).mean())
latc=ok[0][1].latitude.values;lonc=ok[0][1].longitude.values
li=np.where((np.round(latc,3)>=62.25-1e-6)&(np.round(latc,3)<=63.45+1e-6))[0]
lj=np.where((np.round(lonc,3)>=18.73-1e-6)&(np.round(lonc,3)<=19.93+1e-6))[0]
print(latc[li][[0,-1]],lonc[lj][[0,-1]])
A=A[:,li[0]:li[-1]+1,lj[0]:lj[-1]+1]
latr=latc[li];lonr=lonc[lj]
def doy(ix):
    m=ix.month.values;d=ix.day.values
    cum=np.array([0,31,60,91,121,152,182,213,244,274,305,335])
    return cum[m-1]+d
dd=doy(dates)
tgt=(dates>='2012-06-01')
B=A[tgt]
sea=np.isfinite(B).all(0);print(sea.sum(),sea.size)
base=A[~tgt]; bd=dates[~tgt]
# float32->float64 values as stored
bidx=pd.Series(np.arange(len(bd)),index=bd)
bdo=doy(bd)
thr=np.full((366,)+sea.shape,np.nan);clim=thr.copy()
bs=bd[(bd>='1992-01-01')&(bd<='2002-12-31')]
for d in range(1,367):
    if d==60: continue
    idx=set()
    for t in bs[doy(bs)==d]:
        for k in range(-5,6):
            u=t+pd.Timedelta(days=k)
            if u in bidx.index: idx.add(bidx[u])
    P=base[sorted(idx)][:,sea]
    thr[d-1][sea]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim[d-1][sea]=np.nanmean(P,axis=0)
for a in(thr,clim): a[59]=(a[58]+a[60])/2
def sm(a):
    return np.mean([np.roll(a,-s,axis=0) for s in range(-15,16)],axis=0)
thr=sm(thr)
td=dates[tgt];tdo=doy(td)
hot=(B>=thr[tdo-1])&sea
def runs(h):
    out=np.zeros_like(h)
    T=len(h);i=0
    segs=[]
    while i<T:
        if h[i]:
            j=i
            while j<T and h[j]:j+=1
            if j-i>=5:segs.append([i,j])
            i=j
        else:i+=1
    merged=[]
    for s in segs:
        if merged and s[0]-merged[-1][1]<=2: merged[-1][1]=s[1]
        else: merged.append(s)
    for s,e in merged: out[s:e]=True
    return out
M=np.zeros(hot.shape,bool)
for i,j in zip(*np.where(sea)): M[:,i,j]=runs(hot[:,i,j])
act=M.any((1,2))
ev=[];i=0
while i<len(act):
    if act[i]:
        j=i
        while j+1<len(act) and act[j+1]:j+=1
        ev.append({"onset":f"{td[i]:%Y-%m-%d}","end":f"{td[j]:%Y-%m-%d}"});i=j+1
    else:i+=1
print(ev,M.sum())
ds=xr.Dataset({'mhw':(('time','lat','lon'),M.astype('uint8'))},coords={'time':td,'lat':latr,'lon':lonr})
ds.to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":62.25,"lat_max":63.45,"lon_min":18.73,"lon_max":19.93},
"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
"target_analysed":{"start":"2012-06-01","end":"2012-08-31"},
"events":ev,"complete":True,"caveats":"Baseline pools also used 1991-12-27..31 and 2003-01-01..05 per spec."},open('output/report.json','w'))