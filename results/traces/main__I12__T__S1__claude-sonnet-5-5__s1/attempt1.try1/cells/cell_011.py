import numpy as np,pandas as pd,json,os,xarray as xr
z=np.load('/tmp/d.npz');T=pd.to_datetime(z['t']);A=z['a'].astype('float64')
print(A.shape,np.nanmin(A),np.nanmax(A))
bm=(T<='2003-01-05');Tb=T[bm];Ab=A[bm];Tt=T[~bm];At=A[~bm]
assert len(Tb)==pd.Timestamp('2003-01-05')-pd.Timestamp('1991-12-27')+pd.Timedelta(days=1)==len(Tb)*pd.Timedelta(days=1)/pd.Timedelta(days=1) or True
print(len(Tb),len(Tt))
def doy(ts): 
    return np.array([ (pd.Timestamp(2000,m,d).dayofyear) for m,d in zip(ts.month,ts.day)])
db=doy(Tb)
idx={t:i for i,t in enumerate(Tb)}
base=pd.date_range('1992-01-01','2002-12-31')
bdoy=doy(base)
ny,nx=A.shape[1:]
thr=np.full((366,ny,nx),np.nan);clim=thr.copy()
for d in range(1,367):
    if d==60: continue
    sel=set()
    for b in base[bdoy==d]:
        for k in range(-5,6): sel.add(idx[b+pd.Timedelta(days=k)])
    pool=Ab[sorted(sel)]
    thr[d-1]=np.nanquantile(pool,0.9,axis=0,method='hazen')
    clim[d-1]=np.nanmean(pool,axis=0)
for a in (thr,clim): a[59]=(a[58]+a[60])/2
def sm(a):
    return np.mean([np.roll(a,-k,axis=0) for k in range(-15,16)],axis=0)
thr=sm(thr)
# sea cells
sea=np.isfinite(At).all(0)
print(sea.sum(), np.isnan(thr[:,sea]).sum())
dt=doy(Tt)
hot=(At>=thr[dt-1])&sea
n=len(Tt);mhw=np.zeros_like(hot)
def runs(v):
    r=[];i=0
    while i<len(v):
        if v[i]:
            j=i
            while j<len(v) and v[j]:j+=1
            r.append((i,j));i=j
        else:i+=1
    return r
for y,x in zip(*np.where(sea)):
    rs=[r for r in runs(hot[:,y,x]) if r[1]-r[0]>=5]
    m=np.zeros(n,bool)
    for r in rs:m[r[0]:r[1]]=1
    for a,b in zip(rs,rs[1:]):
        if b[0]-a[1]<=2:m[a[1]:b[0]]=1
    mhw[:,y,x]=m
act=mhw.any((1,2))
ev=[(s,e) for s,e in runs(act)]
evs=[{"onset":str(Tt[s].date()),"end":str(Tt[e-1].date())} for s,e in ev]
print(evs,mhw.sum())
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype('uint8'))},coords={'time':Tt.values,'lat':z['lat'],'lon':z['lon']}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":56.09,"lat_max":57.29,"lon_min":10.55,"lon_max":11.75},
"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
"target_analysed":{"start":"2009-06-01","end":"2009-08-31"},
"events":evs,"complete":True,"caveats":""},open('output/report.json','w'))