import xarray as xr, numpy as np, pandas as pd, json, os
b=xr.open_dataarray("/tmp/b.nc");t=xr.open_dataarray("/tmp/t.nc")
B=b.values.astype(np.float64);T=t.values.astype(np.float64)
bt=pd.DatetimeIndex(b.time.values)
def doy(ix):
    m=np.array(ix.month);dd=np.array(ix.day)
    cum=np.cumsum([0,31,29,31,30,31,30,31,31,30,31,30])
    return cum[m-1]+dd
idx={x:i for i,x in enumerate(bt)}
bd=pd.date_range("1992-01-01","2002-12-31");bdoy=doy(bd)
thr=np.full((366,)+B.shape[1:],np.nan)
for dd in range(1,367):
    if dd==60: continue
    ii=[]
    for dt in bd[bdoy==dd]:
        for o in range(-5,6): ii.append(idx[dt+pd.Timedelta(days=o)])
    thr[dd-1]=np.nanquantile(B[ii],0.9,axis=0,method="hazen")
thr[59]=(thr[58]+thr[60])/2
thr=sum(np.roll(thr,-k,axis=0) for k in range(-15,16))/31
sea=np.isfinite(T).all(0)
td=pd.date_range("2021-06-01","2021-08-31");tdo=doy(td)
hot=(T>=thr[tdo-1])&sea
def runs(x):
    r=[];i=0;n=len(x)
    while i<n:
        if x[i]:
            j=i
            while j+1<n and x[j+1]: j+=1
            r.append((i,j));i=j+1
        else:i+=1
    return r
mhw=np.zeros(hot.shape,np.uint8)
for a in range(hot.shape[1]):
  for c in range(hot.shape[2]):
    if not sea[a,c]: continue
    r=[x for x in runs(hot[:,a,c]) if x[1]-x[0]+1>=5]
    m=[]
    for x in r:
        if m and x[0]-m[-1][1]-1<=2: m[-1]=(m[-1][0],x[1])
        else: m.append(x)
    for x in m: mhw[x[0]:x[1]+1,a,c]=1
act=mhw.any((1,2))
ev=[{"onset":str(td[s].date()),"end":str(td[e].date())} for s,e in runs(act)]
print(sea.sum(),ev)
os.makedirs("output",exist_ok=True)
xr.Dataset({"mhw":(("time","lat","lon"),mhw)},coords={"time":td,"lat":t.latitude.values,"lon":t.longitude.values}).to_netcdf("output/mhw_mask.nc")
json.dump({"region":{"lat_min":56.09,"lat_max":57.29,"lon_min":10.55,"lon_max":11.75},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2021-06-01","end":"2021-08-31"},"events":ev,"complete":True,"caveats":""},open("output/report.json","w"))