import json,os,numpy as np,pandas as pd,xarray as xr
lat=np.load('/work/lat.npy');lon=np.load('/work/lon.npy')
bd=pd.date_range('1991-12-27','2003-01-05')
B=np.stack([np.load(f'/work/d/sst_{t:%Y%m%d}.nc.npy') for t in bd]).astype(np.float64)[:,1:61,0:61]
td=pd.date_range('2007-06-01','2007-08-31')
T=np.stack([np.load(f'/work/d/sst_{t:%Y%m%d}.nc.npy') for t in td]).astype(np.float64)[:,1:61,0:61]
sea=np.isfinite(T).all(0); print(sea.sum())
cum=np.cumsum([0,31,29,31,30,31,30,31,31,30,31,30])
dy=np.array([cum[t.month-1]+t.day for t in bd])
cen=[i for i,t in enumerate(bd) if pd.Timestamp('1992-01-01')<=t<=pd.Timestamp('2002-12-31')]
thr=np.full((366,)+sea.shape,np.nan)
for d in range(1,367):
    if d==60: continue
    idx=set()
    for i in cen:
        if dy[i]==d: idx.update(range(i-5,i+6))
    pool=B[sorted(idx)][:,sea]
    t=np.full(sea.shape,np.nan)
    t[sea]=np.nanquantile(pool,0.9,axis=0,method='hazen')
    thr[d-1]=t
thr[59]=(thr[58]+thr[60])/2
thr=np.mean([np.roll(thr,-k,0) for k in range(-15,16)],0)
tdy=np.array([cum[t.month-1]+t.day for t in td])
hot=(T>=thr[tdy-1])&sea
n=len(td);m=np.zeros(hot.shape,bool)
for i,j in np.ndindex(sea.shape):
    if not sea[i,j]: continue
    h=hot[:,i,j]; runs=[];k=0
    while k<n:
        if h[k]:
            e=k
            while e<n and h[e]: e+=1
            if e-k>=5: runs.append([k,e-1])
            k=e
        else:k+=1
    mer=[]
    for r in runs:
        if mer and r[0]-mer[-1][1]-1<=2: mer[-1][1]=r[1]
        else: mer.append(r)
    for s,e in mer: m[s:e+1,i,j]=True
act=m.any((1,2));ev=[];k=0
while k<n:
    if act[k]:
        e=k
        while e+1<n and act[e+1]: e+=1
        ev.append({"onset":str(td[k].date()),"end":str(td[e].date())});k=e+1
    else:k+=1
print(ev,m.sum())
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),m.astype('uint8'))},coords={'time':td,'lat':lat[1:61],'lon':lon[0:61]}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":59.93,"lat_max":61.13,"lon_min":18.69,"lon_max":19.89},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2007-06-01","end":"2007-08-31"},"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))