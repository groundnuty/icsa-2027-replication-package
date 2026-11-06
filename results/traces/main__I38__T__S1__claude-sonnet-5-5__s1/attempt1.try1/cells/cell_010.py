import numpy as np,pandas as pd,json,xarray as xr
S=np.load('output/sst.npy').astype('float64');la,lo=np.load('output/ll.npy',allow_pickle=True)
la=la.astype('float32');lo=lo.astype('float32')
dates=pd.date_range('1991-12-27','2003-08-31')
def doy(ts):
    return np.array([ (pd.Timestamp(2000,t.month,t.day).dayofyear) for t in ts])
dy=doy(dates)
bs=np.where((dates>='1992-01-01')&(dates<='2002-12-31'))[0]
ti=np.where((dates>='2003-06-01')&(dates<='2003-08-31'))[0]
sea=np.isfinite(S[ti]).all(0)
ny,nx=sea.shape
thr=np.full((366,ny,nx),np.nan);clim=thr.copy()
for d in range(1,367):
    if d==60: continue
    idx=set()
    for b in bs:
        if dy[b]==d: idx.update(range(b-5,b+6))
    idx=sorted(i for i in idx if 0<=i<len(dates))
    pool=S[idx]
    thr[d-1]=np.nanquantile(pool,0.9,axis=0,method='hazen')
    clim[d-1]=np.nanmean(pool,axis=0)
for a in (thr,clim): a[59]=(a[58]+a[60])/2
def sm(a):
    return np.mean([np.roll(a,-k,axis=0) for k in range(-15,16)],axis=0)
thr=sm(thr)
T=S[ti];hot=(T>=thr[dy[ti]-1])&sea
def runs(x):
    out=[];i=0;n=len(x)
    while i<n:
        if x[i]:
            j=i
            while j<n and x[j]: j+=1
            out.append((i,j));i=j
        else: i+=1
    return out
M=np.zeros(hot.shape,bool)
for a in range(ny):
  for b in range(nx):
    if not sea[a,b]: continue
    r=[q for q in runs(hot[:,a,b]) if q[1]-q[0]>=5]
    if not r: continue
    m=[list(r[0])]
    for s,e in r[1:]:
        if s-m[-1][1]<=2: m[-1][1]=e
        else: m.append([s,e])
    for s,e in m: M[s:e,a,b]=True
act=M.any((1,2));ev=[];i=0
while i<len(act):
    if act[i]:
        j=i
        while j<len(act) and act[j]: j+=1
        ev.append({"onset":str(dates[ti][i].date()),"end":str(dates[ti][j-1].date())});i=j
    else:i+=1
print(sea.sum(),M.sum(),ev)
t=dates[ti]
xr.Dataset({'mhw':(('time','lat','lon'),M.astype('uint8'))},coords={'time':t,'lat':la,'lon':lo}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":60.49,"lat_max":61.69,"lon_min":17.25,"lon_max":18.45},
"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
"target_analysed":{"start":"2003-06-01","end":"2003-08-31"},"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))