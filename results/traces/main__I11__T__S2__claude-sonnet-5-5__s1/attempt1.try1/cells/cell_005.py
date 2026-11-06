dates=pd.DatetimeIndex(t[i0:i1])
def doy(ix):
    m=ix.month.values;dd=ix.day.values
    cum=np.cumsum([0,31,29,31,30,31,30,31,31,30,31,30])
    return cum[m-1]+dd
D=doy(dates)
bs=np.where((dates>='1992-01-01')&(dates<='2002-12-31'))[0]
n=len(dates)
thr=np.full((366,60,60),np.nan);clim=thr.copy()
for d in range(1,367):
    if d==60: continue
    idx=set()
    for c in bs[D[bs]==d]:
        idx.update(range(max(0,c-5),min(n,c+6)))
    P=B[sorted(idx)]
    thr[d-1]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim[d-1]=np.nanmean(P,axis=0)
for a in(thr,clim): a[59]=(a[58]+a[60])/2
def sm(a):
    return sum(np.roll(a,-k,axis=0) for k in range(-15,16))/31
thr=sm(thr)
Td=doy(pd.DatetimeIndex(t[j0:j1]))
sea=np.isfinite(T).all(0)
hot=(T>=thr[Td-1])&sea
nt=len(Td);mhw=np.zeros(hot.shape,bool)
for i in range(60):
  for j in range(60):
    if not sea[i,j]: continue
    h=hot[:,i,j];runs=[];s=None
    for k in range(nt+1):
        if k<nt and h[k]:
            if s is None:s=k
        elif s is not None:
            if k-s>=5:runs.append([s,k-1])
            s=None
    merged=[]
    for r in runs:
        if merged and r[0]-merged[-1][1]-1<=2: merged[-1][1]=r[1]
        else: merged.append(r)
    for a,b in merged: mhw[a:b+1,i,j]=True
act=mhw.any((1,2))
days=pd.DatetimeIndex(t[j0:j1]);ev=[];s=None
for k in range(nt+1):
    if k<nt and act[k]:
        if s is None:s=k
    elif s is not None:
        ev.append({"onset":str(days[s].date()),"end":str(days[k-1].date())});s=None
print(sea.sum(),ev)
import os,json
os.makedirs('output',exist_ok=True)
o=xr.Dataset({"mhw":(("time","lat","lon"),mhw.astype('uint8'))},coords={"time":days,"lat":sub.latitude.values,"lon":sub.longitude.values})
o.to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":55.67,"lat_max":56.87,"lon_min":16.45,"lon_max":17.65},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2021-06-01","end":"2021-08-31"},"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))