
import xarray as xr, numpy as np, pandas as pd, json, os, warnings
warnings.filterwarnings('ignore')
d=np.load('/tmp/w/d.npz')
base=d['base']; btime=pd.to_datetime(d['btime']); tv=d['tv']; ttime=pd.to_datetime(d['ttime']); latv=d['lat']; lonv=d['lon']
ny,nx=base.shape[1:]
ref=pd.date_range('2000-01-01','2000-12-31')
md2doy={(t.month,t.day):t.day_of_year for t in ref}
doy_of=lambda idx: np.array([md2doy[(t.month,t.day)] for t in idx])
tdoy=doy_of(ttime)
sea=np.isfinite(tv).all(axis=0)
thr=np.full((367,ny,nx),np.nan)
for doy in range(1,367):
    if doy==60: continue
    md=ref[doy-1]; pool=[]
    for y in range(1992,2003):
        s=pd.Timestamp(year=y,month=md.month,day=md.day)
        pool.append(np.where((btime>=s-pd.Timedelta(days=5))&(btime<=s+pd.Timedelta(days=5)))[0])
    idx=np.unique(np.concatenate(pool))
    thr[doy]=np.nanquantile(base[idx],0.9,axis=0,method='hazen')
thr[60]=(thr[59]+thr[61])/2
a=thr[1:367]; T=np.empty_like(a)
for i in range(366):
    T[i]=a[[(i+k)%366 for k in range(-15,16)]].mean(axis=0)
Tt=T[tdoy-1]
hot=(tv>=Tt)&sea[None]
def runs(b):
    r=[];i=0;n=len(b)
    while i<n:
        if b[i]:
            j=i
            while j+1<n and b[j+1]: j+=1
            r.append((i,j)); i=j+1
        else: i+=1
    return r
nt=len(ttime); mhw=np.zeros((nt,ny,nx),bool)
for y in range(ny):
    for x in range(nx):
        if not sea[y,x]: continue
        rr=[r for r in runs(hot[:,y,x]) if r[1]-r[0]+1>=5]
        if not rr: continue
        groups=[list(rr[0])]
        for s,e in rr[1:]:
            if s-groups[-1][1]-1<=2: groups[-1][1]=e
            else: groups.append([s,e])
        for s,e in groups: mhw[s:e+1,y,x]=True
active=mhw.any(axis=(1,2))
ev=[];i=0
while i<nt:
    if active[i]:
        j=i
        while j+1<nt and active[j+1]: j+=1
        ev.append({"onset":str(ttime[i].date()),"end":str(ttime[j].date())}); i=j+1
    else: i+=1
os.makedirs('output',exist_ok=True)
out=xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype(np.uint8))},
               coords={'time':ttime.values,'lat':latv.astype(np.float32),'lon':lonv.astype(np.float32)})
out.to_netcdf('output/mhw_mask.nc',engine='h5netcdf')
rep={"region":{"lat_min":56.13,"lat_max":57.33,"lon_min":17.71,"lon_max":18.91},
     "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
     "target_analysed":{"start":"2019-06-01","end":"2019-08-31"},
     "events":ev,"complete":True,
     "caveats":"Day-of-year uses the fixed leap-year table (Mar 1 = 61 in all years) as specified. Land cells (300 of 3600) are NaN and written as 0. Baseline pools use calendar windows extending into 1991-12-27..1991-12-31 and 2003-01-01..2003-01-05. Only one regional event found."}
json.dump(rep,open('output/report.json','w'),indent=2)
chk=xr.open_dataset('output/mhw_mask.nc',engine='h5netcdf')
print(ev, chk.mhw.dims, chk.mhw.shape, chk.mhw.dtype, int(chk.mhw.values.sum()), int(mhw.sum()))
