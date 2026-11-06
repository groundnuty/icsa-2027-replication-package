
s=xr.open_dataarray('/tmp/s.nc');tg=xr.open_dataarray('/tmp/tg.nc')
tt=pd.DatetimeIndex(s.time.values);V=s.values.astype('float64')
def doy(i): 
    return np.array([(pd.Timestamp(2000,x.month,x.day).dayofyear) for x in i])
D=doy(tt)
bidx=np.where((tt>='1992-01-01')&(tt<='2002-12-31'))[0]
thr=np.full((366,60,60),np.nan);clim=thr.copy()
for d in range(1,367):
    if d==60: continue
    ids=[]
    for b in bidx:
        if D[b]==d: ids+=list(range(b-5,b+6))
    p=V[ids]
    thr[d-1]=np.nanquantile(p,0.9,axis=0,method='hazen');clim[d-1]=np.nanmean(p,axis=0)
for a in (thr,clim): a[59]=(a[58]+a[60])/2
def sm(a):
    return sum(np.roll(a,k,axis=0) for k in range(-15,16))/31
thr=sm(thr)
tv=tg.values.astype('float64');td=doy(pd.DatetimeIndex(tg.time.values))
sea=np.isfinite(tv).all(0)
hot=(tv>=thr[td-1])&sea
T=len(td);m=np.zeros_like(hot)
for i in range(60):
  for j in range(60):
    if not sea[i,j]: continue
    h=hot[:,i,j];runs=[];k=0
    while k<T:
        if h[k]:
            e=k
            while e<T and h[e]:e+=1
            if e-k>=5:runs.append([k,e])
            k=e
        else:k+=1
    mer=[]
    for r in runs:
        if mer and r[0]-mer[-1][1]<=2: mer[-1][1]=r[1]
        else: mer.append(r)
    for a,b in mer:m[a:b,i,j]=True
act=m.any((1,2));ev=[];k=0
dates=pd.DatetimeIndex(tg.time.values)
while k<T:
    if act[k]:
        e=k
        while e+1<T and act[e+1]:e+=1
        ev.append({"onset":str(dates[k].date()),"end":str(dates[e].date())});k=e+1
    else:k+=1
print(ev,sea.sum())
import os,json
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),m.astype('uint8'))},coords={'time':tg.time.values,'lat':tg.latitude.values,'lon':tg.longitude.values}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":60.09,"lat_max":61.29,"lon_min":20.01,"lon_max":21.21},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2012-06-01","end":"2012-08-31"},"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))
