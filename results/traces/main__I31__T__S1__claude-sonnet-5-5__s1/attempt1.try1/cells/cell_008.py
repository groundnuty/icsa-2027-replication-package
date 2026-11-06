import pickle,numpy as np,pandas as pd,xarray as xr,json,os
dates,res=pickle.load(open('/tmp/cache.pkl','rb'))
lat=res[0][2];lon=res[0][3]
S=np.stack([r[1] for r in res]).astype('float64')  # note float32 stored values -> float64
dates=pd.DatetimeIndex(dates)
nb=(dates<='2003-01-05').sum()
B=S[:nb];bd=dates[:nb];T=S[nb:];td=dates[nb:]
print(np.nanmean(T[0]),np.isfinite(T).all(0).sum())
sea=np.isfinite(T).all(0)
def doy(ix):
    m=ix.month.values;d=ix.day.values
    cum=np.array([0,31,60,91,121,152,182,213,244,274,305,335])
    return cum[m-1]+d
bdoy=doy(bd)
base_mask=(bd>='1992-01-01')&(bd<='2002-12-31')
ndays=len(bd);pos=np.arange(ndays)
thr=np.full((366,)+sea.shape,np.nan);clim=thr.copy()
Bs=B[:,sea]
th=np.full((366,Bs.shape[1]),np.nan);cl=th.copy()
for d in range(1,367):
    if d==60: continue
    centers=np.where(base_mask&(bdoy==d))[0]
    idx=np.unique(np.concatenate([np.arange(c-5,c+6) for c in centers]))
    idx=idx[(idx>=0)&(idx<ndays)]
    P=Bs[idx]
    th[d-1]=np.nanquantile(P,0.9,axis=0,method='hazen');cl[d-1]=np.nanmean(P,axis=0)
for a in(th,cl): a[59]=(a[58]+a[60])/2
def sm(a):
    return sum(np.roll(a,k,axis=0) for k in range(-15,16))/31
th=sm(th)
tdoy=doy(td)
hot=np.zeros(T.shape,bool)
hot[:,sea]=T[:,sea]>=th[tdoy-1]
def runs(h):
    out=np.zeros_like(h);n=len(h);i=0
    segs=[]
    while i<n:
        if h[i]:
            j=i
            while j<n and h[j]:j+=1
            if j-i>=5:segs.append([i,j])
            i=j
        else:i+=1
    merged=[]
    for s in segs:
        if merged and s[0]-merged[-1][1]<=2: merged[-1][1]=s[1]
        else: merged.append(s)
    for a,b in merged: out[a:b]=True
    return out
M=np.zeros(T.shape,bool)
for i,j in zip(*np.where(sea)): M[:,i,j]=runs(hot[:,i,j])
act=M.any((1,2))
ev=[];i=0
while i<len(act):
    if act[i]:
        j=i
        while j+1<len(act) and act[j+1]:j+=1
        ev.append({"onset":str(td[i].date()),"end":str(td[j].date())});i=j+1
    else:i+=1
print(ev,M.sum())
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),M.astype('uint8'))},coords={'time':td.values,'lat':lat,'lon':lon}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":58.69,"lat_max":59.89,"lon_min":18.69,"lon_max":19.89},
"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
"target_analysed":{"start":"2017-06-01","end":"2017-08-31"},
"events":ev,"complete":True,"caveats":"Window pools used 1991-12-27..2003-01-05 as specified."},open('output/report.json','w'))