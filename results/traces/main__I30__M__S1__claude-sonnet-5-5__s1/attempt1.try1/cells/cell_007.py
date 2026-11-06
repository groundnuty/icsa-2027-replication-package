import os,numpy as np,pandas as pd,xarray as xr,pickle,json
days,res=pickle.load(open('/tmp/c.pkl','rb'))
nb=len(pd.date_range('1991-12-27','2003-01-05'))
B=np.stack([r[0] for r in res[:nb]]);T=np.stack([r[0] for r in res[nb:]])
lat,lon=res[0][1],res[0][2]
bd=pd.DatetimeIndex(days[:nb])
cum=np.array([0,31,60,91,121,152,182,213,244,274,305,335])
def dy(ix): return cum[ix.month-1]+ix.day
bdoy=dy(bd)
sea=np.isfinite(T).all(0);print(sea.sum())
core=np.where((bd>=pd.Timestamp('1992-01-01'))&(bd<=pd.Timestamp('2002-12-31')))[0]
thr=np.full((366,)+sea.shape,np.nan)
for d in range(1,367):
    if d==60: continue
    idx=set()
    for i in core:
        if bdoy[i]==d: idx.update(range(max(0,i-5),min(nb,i+6)))
    P=B[sorted(idx)][:,sea]
    thr[d-1][sea]=np.nanquantile(P,0.9,axis=0,method='hazen')
thr[59]=(thr[58]+thr[60])/2
thr=np.mean([np.roll(thr,-k,axis=0) for k in range(-15,16)],axis=0)
td=pd.date_range('2010-06-01','2010-08-31');tdoy=dy(td)
hot=(T>=thr[tdoy-1])&sea
n=len(td);mhw=np.zeros(hot.shape,bool)
for i,j in np.ndindex(sea.shape):
    if not sea[i,j]: continue
    h=hot[:,i,j];runs=[];s=None
    for t in range(n+1):
        if t<n and h[t]:
            if s is None:s=t
        elif s is not None:
            if t-s>=5: runs.append([s,t-1])
            s=None
    m=[]
    for r in runs:
        if m and r[0]-m[-1][1]-1<=2: m[-1][1]=r[1]
        else: m.append(r)
    for a,b in m: mhw[a:b+1,i,j]=1
act=mhw.any((1,2));ev=[];s=None
for t in range(n+1):
    if t<n and act[t]:
        if s is None:s=t
    elif s is not None:
        ev.append({"onset":str(td[s].date()),"end":str(td[t-1].date())});s=None
print(ev,mhw.sum())
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype('uint8'))},coords={'time':td,'lat':lat,'lon':lon}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":58.69,"lat_max":59.89,"lon_min":18.69,"lon_max":19.89},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2010-06-01","end":"2010-08-31"},"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))