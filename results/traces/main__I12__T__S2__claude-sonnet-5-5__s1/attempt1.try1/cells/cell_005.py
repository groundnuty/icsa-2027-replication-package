sub=xr.open_dataarray('/tmp/sub.nc');tg=xr.open_dataarray('/tmp/tg.nc')
T=pd.DatetimeIndex(sub.time.values);v=sub.values.astype(np.float64)
def doy(t): 
    return np.array([ (pd.Timestamp(2000,x.month,x.day).dayofyear) for x in t])
D=doy(T)
bidx=np.where((T>='1992-01-01')&(T<='2002-12-31'))[0]
thr=np.full((366,)+v.shape[1:],np.nan);clim=thr.copy()
for d in range(1,367):
    if d==60: continue
    ids=sorted({j for i in bidx[D[bidx]==d] for j in range(i-5,i+6) if 0<=j<len(T)})
    pool=v[ids]
    thr[d-1]=np.nanquantile(pool,0.9,axis=0,method='hazen')
    clim[d-1]=np.nanmean(pool,axis=0)
for x in(thr,clim): x[59]=(x[58]+x[60])/2
def sm(x):
    return np.mean([np.roll(x,-k,axis=0) for k in range(-15,16)],axis=0)
thr=sm(thr)
tv=tg.values.astype(np.float64);TT=pd.DatetimeIndex(tg.time.values)
sea=np.isfinite(tv).all(0)
Dt=doy(TT)
hot=(tv>=thr[Dt-1])&sea
nt=len(TT);m=np.zeros(hot.shape,bool)
for i in range(60):
  for j in range(60):
    if not sea[i,j]: continue
    h=hot[:,i,j];runs=[];s=None
    for t in range(nt+1):
        if t<nt and h[t]:
            if s is None:s=t
        else:
            if s is not None:
                if t-s>=5:runs.append([s,t-1])
                s=None
    mg=[]
    for r in runs:
        if mg and r[0]-mg[-1][1]-1<=2: mg[-1][1]=r[1]
        else: mg.append(r)
    for a_,b in mg:m[a_:b+1,i,j]=True
act=m.any((1,2));ev=[];s=None
for t in range(nt+1):
    if t<nt and act[t]:
        if s is None:s=t
    elif s is not None: ev.append({"onset":str(TT[s].date()),"end":str(TT[t-1].date())});s=None
print(sea.sum(),ev)
import os,json
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),m.astype(np.uint8))},coords={'time':tg.time.values,'lat':tg.latitude.values,'lon':tg.longitude.values}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":56.09,"lat_max":57.29,"lon_min":10.55,"lon_max":11.75},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2009-06-01","end":"2009-08-31"},"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))