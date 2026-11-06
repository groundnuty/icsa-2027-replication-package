code=r'''
import numpy as np, pandas as pd, pickle, json, os
need,data,la,lo=pickle.load(open('/tmp/c.pkl','rb'))
idx={d:i for i,d in enumerate(need)}
def doy(d): return (pd.Timestamp(2000,d.month,d.day).dayofyear)  # leap-year mapping
base=pd.date_range('1992-01-01','2002-12-31')
tgt=pd.date_range('2021-06-01','2021-08-31')
T=data[[idx[d] for d in tgt]]
sea=np.isfinite(T).all(0)
thr=np.full((366,)+sea.shape,np.nan); clim=thr.copy()
bd={}
for d in base: bd.setdefault(doy(d),[]).append(d)
for k in range(1,367):
    if k==60: continue
    ii=[idx[c+pd.Timedelta(days=o)] for c in bd[k] for o in range(-5,6)]
    pool=data[ii]
    thr[k-1]=np.nanquantile(pool,0.9,axis=0,method='hazen')
    clim[k-1]=np.nanmean(pool,axis=0)
for a in (thr,clim): a[59]=(a[58]+a[60])/2
def sm(a):
    return sum(np.roll(a,-s,axis=0) for s in range(-15,16))/31
thr=sm(thr)
doys=np.array([doy(d) for d in tgt])
hot=(T>=thr[doys-1])&sea
n=len(tgt); mhw=np.zeros_like(hot)
def runs(x):
    r=[];s=None
    for i,v in enumerate(list(x)+[False]):
        if v and s is None:s=i
        if not v and s is not None:r.append((s,i-1));s=None
    return r
for a,b in zip(*[c.ravel() for c in np.indices(sea.shape)]):
    if not sea[a,b]: continue
    rs=[r for r in runs(hot[:,a,b]) if r[1]-r[0]+1>=5]
    if not rs: continue
    m=[list(rs[0])]
    for s,e in rs[1:]:
        if s-m[-1][1]-1<=2: m[-1][1]=e
        else: m.append([s,e])
    for s,e in m: mhw[s:e+1,a,b]=True
act=mhw.any((1,2))
ev=[(s,e) for s,e in runs(act)]
print(sea.sum(),mhw.sum(),ev)
import xarray as xr
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype('uint8'))},coords={'time':tgt,'lat':la,'lon':lo}).to_netcdf('output/mhw_mask.nc')
f=lambda i:str(tgt[i].date())
json.dump({"region":{"lat_min":61.57,"lat_max":62.77,"lon_min":20.17,"lon_max":21.37},
"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
"target_analysed":{"start":"2021-06-01","end":"2021-08-31"},
"events":[{"onset":f(s),"end":f(e)} for s,e in ev],"complete":True,"caveats":""},open('output/report.json','w'),indent=1)
'''
open('/tmp/m.py','w').write(code)
r=subprocess.run(['python','/tmp/m.py'],capture_output=True,text=True);print(r.stdout[-3000:],r.stderr[-2000:])