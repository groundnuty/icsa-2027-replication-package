
import json, os
from datetime import date, timedelta
# day-of-year mapping: leap reference year 2000
def doy_of(d):
    ref=pd.Timestamp(2000,d.month,d.day)
    return ref.dayofyear  # 2000 leap: Feb29=60, Mar1=61
dates=pd.DatetimeIndex(t)
ext_start=pd.Timestamp('1991-12-27'); ext_end=pd.Timestamp('2003-01-05')
# extended-range SST index
full=xarray.open_dataset('/work/sst_s2.nc',engine='h5netcdf')
ex_mask=(dates>=ext_start)&(dates<=ext_end)
Xe=X[ex_mask]; site_f=dates[ex_mask]
assert len(site_f)==(ext_end-ext_start).days+1
# baseline dates
bstart=pd.Timestamp('1992-01-01'); bend=pd.Timestamp('2002-12-31')
bdates=pd.date_range(bstart,bend)
doy_b=np.array([doy_of(x.date()) for x in bdates])
pos={d:i for i,d in enumerate(site_f)}
ncell=X.shape[1]
thr=np.full((367,ncell),np.nan); clim=np.full((367,ncell),np.nan)
for d in range(1,367):
    if d==60: continue
    bl=bdates[doy_b==d]
    idx=[]
    for b in bl:
        for k in range(-5,6):
            idx.append(pos[b+pd.Timedelta(days=k)])
    idx=np.array(sorted(set(idx)))
    P=Xe[idx][:,fin]
    thr[d,fin]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim[d,fin]=np.nanmean(P,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    b=a[1:367]  # days 1..366 -> index 0..365
    out=np.empty_like(b)
    for i in range(366):
        ii=[(i+k)%366 for k in range(-15,16)]
        out[i]=b[ii].mean(axis=0)
    r=np.full_like(a,np.nan); r[1:367]=out; return r
thrS=smooth(thr); climS=smooth(clim)
# target days
tdates=dates[tgt]; Xt=X[tgt]
tdoy=np.array([doy_of(x.date()) for x in tdates])
print('days',len(tdates), tdoy[:3], tdoy[-1], 'thr sample', thrS[153,fin][:3])
hot=np.zeros(Xt.shape,bool)
hot[:,fin]=Xt[:,fin]>=thrS[tdoy][:,fin]
# per-cell MHW
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
    # join gaps of 1-2 days
    merged=[]
    for r in runs:
        if merged and (r[0]-merged[-1][1]-1) in (1,2):
            merged[-1][1]=r[1]
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
# write outputs
os.makedirs('output',exist_ok=True)
M=np.zeros((nT,len(la[ri]),len(lo[ci])),np.uint8)
M.reshape(nT,-1)[:]=mhw.astype(np.uint8)
out=xarray.Dataset({'mhw':(('time','lat','lon'),M)},
    coords={'time':sub.time.values[tgt],'lat':la[ri],'lon':lo[ci]})
out.to_netcdf('output/mhw_mask.nc')
rep={"region":{"lat_min":57.13,"lat_max":58.33,"lon_min":22.79,"lon_max":23.99},
 "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
 "target_analysed":{"start":"2014-06-01","end":"2014-08-31"},
 "events":events,"complete":True,
 "caveats":"Sea cells: 3301 of 3600 region cells with finite SST on all target days; other cells masked 0. Day-of-year from fixed month/day table (Feb 29=60). Baseline windows drew on extension days 1991-12-27..31 and 2003-01-01..05. Quantile via numpy hazen method. Target days dated 2014-06-01..2014-08-31 (92 days)."}
json.dump(rep,open('output/report.json','w'),indent=1)
print(open('output/report.json').read()[:300])
