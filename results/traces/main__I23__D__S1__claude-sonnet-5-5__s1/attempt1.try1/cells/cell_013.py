import numpy as np,pandas as pd,json,os,xarray as xr
z=np.load('/work/data.npz');sst=z['sst'];lat=z['lat'];lon=z['lon'];ds=pd.DatetimeIndex(z['dates'])
nb=(ds<='2003-01-05').sum();base=sst[:nb];bd=ds[:nb];tg=sst[nb:];td=ds[nb:]
doy=lambda i:pd.Timestamp(2000,i.month,i.day).day_of_year
sea=np.isfinite(tg).all(0)
dd=np.array([doy(i) for i in bd])
thr=np.full((366,)+sst.shape[1:],np.nan)
off=np.arange(-5,6)
for d in range(1,367):
    if d==60: continue
    idx=np.where((dd==d)&(bd>='1992-01-01')&(bd<='2002-12-31'))[0]
    ii=np.unique((idx[:,None]+off).ravel());ii=ii[(ii>=0)&(ii<nb)]
    thr[d-1]=np.nanquantile(base[ii][:, sea],0.9,axis=0,method='hazen').__array__().reshape(-1)[0:0].tolist() or 0 if False else np.nan
    pool=base[ii]
    thr[d-1]=np.nanquantile(pool,0.9,axis=0,method='hazen')
thr[59]=(thr[58]+thr[60])/2
thr=sum(np.roll(thr,-k,axis=0) for k in range(-15,16))/31
tdoy=np.array([doy(i) for i in td])
hot=(tg>=thr[tdoy-1])&sea
mh=np.zeros_like(hot);T=len(td)
for y in range(60):
  for x in range(60):
    v=hot[:,y,x]
    if not v.any(): continue
    segs=[];i=0
    while i<T:
        if v[i]:
            j=i
            while j<T and v[j]: j+=1
            if j-i>=5: segs.append([i,j])
            i=j
        else:i+=1
    m=[]
    for s in segs:
        if m and s[0]-m[-1][1]<=2: m[-1][1]=s[1]
        else: m.append(list(s))
    for s,e in m: mh[s:e,y,x]=True
act=mh.any((1,2));ev=[];i=0
while i<T:
    if act[i]:
        j=i
        while j+1<T and act[j+1]: j+=1
        ev.append({"onset":td[i].strftime('%Y-%m-%d'),"end":td[j].strftime('%Y-%m-%d')});i=j+1
    else:i+=1
print(ev,mh.sum())
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),mh.astype('uint8'))},coords={'time':td.values,'lat':lat,'lon':lon}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":57.41,"lat_max":58.61,"lon_min":18.69,"lon_max":19.89},
"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2013-06-01","end":"2013-08-31"},
"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))