
import xarray, numpy as np, pandas as pd, json, os, warnings
warnings.filterwarnings('ignore')
ds=xarray.open_dataset('/work/sst_s2.nc',engine='h5netcdf')
la=ds.latitude.values; lo=ds.longitude.values
ri=np.where((la>=57.13-1e-6)&(la<=58.33+1e-6))[0]; ci=np.where((lo>=22.79-1e-6)&(lo<=23.99+1e-6))[0]
sub=ds.analysed_sst.isel(latitude=ri,longitude=ci).load()
t=sub.time.values
X=sub.values.astype(np.float64).reshape(len(t),-1)
tgt=(t>=np.datetime64('2014-06-01'))&(t<=np.datetime64('2014-08-31'))
fin=np.isfinite(X[tgt]).all(axis=0)
dates=pd.DatetimeIndex(t)
def doy_of(d):
    return pd.Timestamp(2000,d.month,d.day).day_of_year
ext_start=pd.Timestamp('1991-12-27'); ext_end=pd.Timestamp('2003-01-05')
ex_mask=(dates>=ext_start)&(dates<=ext_end)
Xe=X[ex_mask]; site_f=dates[ex_mask]
assert len(site_f)==(ext_end-ext_start).days+1
bdates=pd.date_range('1992-01-01','2002-12-31')
doy_b=np.array([doy_of(x.date()) for x in bdates])
pos={d:i for i,d in enumerate(site_f)}
ncell=X.shape[1]
thr=np.full((367,ncell),np.nan); clim=np.full((367,ncell),np.nan)
for d in range(1,367):
    if d==60: continue
    bl=bdates[doy_b==d]
    idx=sorted({pos[b+pd.Timedelta(days=k)] for b in bl for k in range(-5,6)})
    P=Xe[idx][:,fin]
    thr[d,fin]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim[d,fin]=np.nanmean(P,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    b=a[1:367]
    out=np.empty_like(b)
    for i in range(366):
        ii=[(i+k)%366 for k in range(-15,16)]
        out[i]=b[ii].mean(axis=0)
    r=np.full_like(a,np.nan); r[1:367]=out; return r
thrS=smooth(thr); climS=smooth(clim)
tdates=dates[tgt]; Xt=X[tgt]
tdoy=np.array([doy_of(x.date()) for x in tdates])
print('days',len(tdates), tdoy[:3], tdoy[-1], 'nan thr', np.isnan(thrS[1:,fin]).sum(), 'nan clim', np.isnan(climS[1:,fin]).sum())
hot=np.zeros(Xt.shape,bool)
hot[:,fin]=Xt[:,fin]>=thrS[tdoy][:,fin]
mhw=np.zeros(Xt.shape,bool)
nT=len(tdates)
for c in np.where(fin)[0]:
    h=hot[:,c]
    runs=[]; i=0
    while i<nT:
        if h[i]:
            j=i
            while j<nT and h[j]: j+=1
            if j-i>=5: runs.append([i,j-1])
            i=j
        else: i+=1
    merged=[]
    for r in runs:
        if merged and (r[0]-merged[-1][1]-1) in (1,2): merged[-1][1]=r[1]
        else: merged.append(list(r))
    for a,b in merged: mhw[a:b+1,c]=True
active=mhw.any(axis=1)
events=[]; i=0
while i<nT:
    if active[i]:
        j=i
        while j<nT and active[j]: j+=1
        events.append({"onset":str(tdates[i].date()),"end":str(tdates[j-1].date())})
        i=j
    else: i+=1
print(events, mhw.sum(), hot.sum())
os.makedirs('output',exist_ok=True)
M=mhw.astype(np.uint8).reshape(nT,len(la[ri]),len(lo[ci]))
out=xarray.Dataset({'mhw':(('time','lat','lon'),M)},
    coords={'time':t[tgt],'lat':la[ri],'lon':lo[ci]})
out.to_netcdf('output/mhw_mask.nc')
rep={"region":{"lat_min":57.13,"lat_max":58.33,"lon_min":22.79,"lon_max":23.99},
 "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
 "target_analysed":{"start":"2014-06-01","end":"2014-08-31"},
 "events":events,"complete":True,
 "caveats":"Sea cells: %d of %d region cells with finite SST on all target days; other cells masked 0. Day-of-year from fixed month/day table (Feb 29=60). Baseline windows drew on extension days 1991-12-27..31 and 2003-01-01..05. Quantile via numpy hazen method. Target 92 days."%(fin.sum(),fin.size)}
json.dump(rep,open('output/report.json','w'),indent=1)
print(open('output/report.json').read()[:400])
