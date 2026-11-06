
script = r'''
import numpy as np, pandas as pd, json, os, xarray as xr
z=np.load('/work/sub.npz'); A=z['A']; tim_d=pd.DatetimeIndex(z['tim'].view('datetime64[ns]'))
lat=z['lat']; lon=z['lon']
tgt_mask=(tim_d>=pd.Timestamp('2022-06-01'))&(tim_d<=pd.Timestamp('2022-08-31'))
Tt=A[tgt_mask]; tt_dates=tim_d[tgt_mask]
sea=np.all(np.isfinite(Tt),axis=0)
doy_all=np.array([pd.Timestamp(2000,x.month,x.day).day_of_year for x in tim_d])
doy_tgt=doy_all[tgt_mask]
base_mask=(tim_d>=pd.Timestamp('1992-01-01'))&(tim_d<=pd.Timestamp('2002-12-31'))
pos={x:i for i,x in enumerate(tim_d)}
pool_idx={d:[] for d in range(1,367) if d!=60}
for bi in np.where(base_mask)[0]:
    d=doy_all[bi]
    if d==60: continue
    B=tim_d[bi]
    for k in range(-5,6):
        D=B+pd.Timedelta(days=k)
        if D in pos: pool_idx[d].append(pos[D])
thr=np.full((367,)+A.shape[1:],np.nan); clim=np.full_like(thr,np.nan)
for d in pool_idx:
    P=A[pool_idx[d]]
    thr[d]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim[d]=np.nanmean(P,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(x):
    v=x[1:367]; out=np.empty_like(v)
    for i in range(366):
        ids=[(i+k)%366 for k in range(-15,16)]
        out[i]=np.mean(v[ids],axis=0)
    return out
thr_s=smooth(thr)
T=len(doy_tgt); nlat,nlon=A.shape[1:]
thr_t=thr_s[doy_tgt-1]
hot=(Tt>=thr_t)
mhw=np.zeros((T,nlat,nlon),bool)
for i in range(nlat):
    for j in range(nlon):
        if not sea[i,j]: continue
        h=hot[:,i,j]
        runs=[]; k=0
        while k<T:
            if h[k]:
                s=k
                while k<T and h[k]: k+=1
                if k-s>=5: runs.append([s,k-1])
            else: k+=1
        merged=[]
        for r in runs:
            if merged and r[0]-merged[-1][1]-1 in (1,2): merged[-1][1]=r[1]
            else: merged.append(list(r))
        for s,e in merged: mhw[s:e+1,i,j]=True
active=mhw.any(axis=(1,2))
events=[]; k=0
while k<T:
    if active[k]:
        s=k
        while k<T and active[k]: k+=1
        events.append({"onset":str(tt_dates[s].date()),"end":str(tt_dates[k-1].date())})
    else: k+=1
print(events, int(mhw.sum()), int(active.sum()), "nhot", int(hot[:,sea].sum()))
print("threshold range sea", np.nanmin(thr_s[:,sea]), np.nanmax(thr_s[:,sea]))
print("sst range", np.nanmin(Tt[:,sea]), np.nanmax(Tt[:,sea]))
os.makedirs('/work/output',exist_ok=True)
import xarray as xr
full=np.zeros((T,nlat,nlon),np.uint8); full[:]=mhw.astype(np.uint8)
ds_out=xr.Dataset({'mhw':(('time','lat','lon'),full)},
    coords={'time':tt_dates.values,'lat':lat,'lon':lon})
ds_out['mhw'].attrs={'long_name':'marine heatwave flag'}
ds_out.to_netcdf('/work/output/mhw_mask.nc')
report={"region":{"lat_min":54.81,"lat_max":56.01,"lon_min":19.61,"lon_max":20.81},
 "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
 "target_analysed":{"start":"2022-06-01","end":"2022-08-31"},
 "events":events,"complete":True,
 "caveats":"Thresholds from 1992-2002 with +/-5-day windows incl. edges 1991-12-27..2003-01-05; land cells (NaN) set to 0; sea cells defined as finite on all target days. Dataset sst read as stored (kelvin)."}
json.dump(report,open('/work/output/report.json','w'),indent=1)
print(json.dumps(report)[:500])
'''
open('/work/run.py','w').write(script)
import subprocess
r=subprocess.run(['python','/work/run.py'],capture_output=True,text=True,cwd='/work')
print(r.stdout[-3000:], r.stderr[-2000:])
