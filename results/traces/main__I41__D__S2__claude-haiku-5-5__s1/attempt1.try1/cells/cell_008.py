
script = r'''
import warnings; warnings.filterwarnings('ignore')
import xarray as xr, numpy as np, pandas as pd, json, os
os.makedirs('/work/output', exist_ok=True)
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
ilat=np.where((lat>=61.57-1e-6)&(lat<=62.77+1e-6))[0]
ilon=np.where((lon>=20.17-1e-6)&(lon<=21.37+1e-6))[0]
ext_start=pd.Timestamp('1991-12-27'); ext_end=pd.Timestamp('2003-01-05')
tgt_start=pd.Timestamp('2021-06-01'); tgt_end=pd.Timestamp('2021-08-31')
times=pd.DatetimeIndex(ds.time.values)
sel=np.where(((times>=ext_start)&(times<=ext_end))|((times>=tgt_start)&(times<=tgt_end)))[0]
sub=ds.analysed_sst.isel(time=sel, latitude=ilat, longitude=ilon).load()
T=pd.DatetimeIndex(sub.time.values)
A=sub.values.astype(np.float64)
nlat,nlon=len(ilat),len(ilon)
def doy_of(ts):
    return np.array([pd.Timestamp(2000,t.month,t.day).day_of_year for t in ts])
doy_all=doy_of(T)
base_mask=(T>=pd.Timestamp('1992-01-01'))&(T<=pd.Timestamp('2002-12-31'))
base_dates=T[base_mask]; base_doy=doy_all[base_mask]
ext_idx=np.where((T>=ext_start)&(T<=ext_end))[0]
Text=T[ext_idx]; Aext=A[ext_idx]
thr=np.full((367,nlat,nlon),np.nan); clim=np.full((367,nlat,nlon),np.nan)
for d in range(1,367):
    if d==60: continue
    bd=base_dates[base_doy==d]
    if len(bd)==0: continue
    inpool=np.zeros(len(Text),bool)
    for b in bd:
        inpool |= (np.abs((Text-b).days)<=5)
    P=Aext[inpool]
    thr[d]=np.nanpercentile(P,90,axis=0,method='hazen')
    clim[d]=np.nanmean(P,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth366(X):
    out=np.empty_like(X)
    for i in range(366):
        ids=[(i+k)%366 for k in range(-15,16)]
        out[i]=X[ids].mean(axis=0)
    return out
thr_s=smooth366(thr[1:]); clim_s=smooth366(clim[1:])
tmask=(T>=tgt_start)&(T<=tgt_end)
At=A[tmask]; Tt=T[tmask]
sea=np.all(np.isfinite(At),axis=0)
print('sea cells', sea.sum(), 'of', sea.size, 'target days', len(Tt), Tt[0].date(), Tt[-1].date())
dt=doy_of(Tt)
thr_t=thr_s[dt-1]
print('sea cells with NaN threshold on target days:', int(np.sum(sea & np.isnan(thr_t).any(axis=0))))
print('doy range', dt.min(), dt.max(), 'NaN sea thr', int(np.sum(sea[None]&np.isnan(thr_t))))
hot=(At>=thr_t)&sea[None]
mhw=np.zeros(hot.shape,bool)
ntd=hot.shape[0]
for i in range(nlat):
    for j in range(nlon):
        if not sea[i,j]: continue
        h=hot[:,i,j]
        runs=[]; k=0
        while k<ntd:
            if h[k]:
                s=k
                while k<ntd and h[k]: k+=1
                if k-s>=5: runs.append([s,k-1])
            else: k+=1
        merged=[]
        for r in runs:
            if merged and r[0]-merged[-1][1]-1<=2: merged[-1][1]=r[1]
            else: merged.append(list(r))
        for s,e in merged: mhw[s:e+1,i,j]=True
active=mhw.any(axis=(1,2))
events=[]; k=0
while k<ntd:
    if active[k]:
        s=k
        while k<ntd and active[k]: k+=1
        events.append({"onset":str(Tt[s].date()),"end":str(Tt[k-1].date())})
    else: k+=1
print('EVENTS', events, 'mhw cell-days', int(mhw.sum()))
# outputs
latv=ds.latitude.values[ilat]; lonv=ds.longitude.values[ilon]
out=xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype(np.uint8))},
    coords={'time':Tt,'lat':latv,'lon':lonv})
out['mhw'].attrs={'long_name':'marine heatwave per-cell flag'}
out.to_netcdf('/work/output/mhw_mask.nc', engine='h5netcdf')
report={"region":{"lat_min":61.57,"lat_max":62.77,"lon_min":20.17,"lon_max":21.37},
 "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
 "target_analysed":{"start":str(Tt[0].date()),"end":str(Tt[-1].date())},
 "events":events,"complete":True,
 "caveats":"Thresholds use pools from 1991-12-27..2003-01-05 windows; cells with NaN thresholds never hot. Sea cells are those finite on all target days. Mask lat/lon coords are dataset values."}
json.dump(report,open('/work/output/report.json','w'),indent=1)
print(json.dumps(report)[:1500])
'''
open('/work/run.py','w').write(script)
import subprocess
r=subprocess.run(['python','/work/run.py'],capture_output=True,text=True)
print(r.stdout[-6000:]); print(r.stderr[-3000:])
