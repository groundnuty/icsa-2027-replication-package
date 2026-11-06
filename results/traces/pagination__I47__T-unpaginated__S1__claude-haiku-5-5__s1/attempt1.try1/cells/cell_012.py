script = r'''
import numpy as np, pandas as pd, json, os, xarray as xr, warnings
warnings.filterwarnings('ignore')
c=np.load('/tmp/sst_cache.npz')
A=c['A']; days=pd.to_datetime(c['days']); lat=c['lat']; lon=c['lon']
ext=pd.date_range('1991-12-27','2003-01-05')
assert (days[:len(ext)]==ext).all()
SST_b=A[:len(ext)]
T=A[len(ext):]
tdays=days[len(ext):]
def doy(ts):
    out=[]
    for t in ts:
        if t.month==2 and t.day==29: out.append(60); continue
        out.append(pd.Timestamp(year=2000,month=t.month,day=t.day).day_of_year)
    return np.array(out)
doy_ext=doy(ext)
assert doy(pd.DatetimeIndex(['2001-03-01']))[0]==61 and doy(pd.DatetimeIndex(['2001-12-31']))[0]==366
bl_idx=np.where((ext>=pd.Timestamp('1992-01-01'))&(ext<=pd.Timestamp('2002-12-31')))[0]
ny,nx=lat.size,lon.size
thr=np.full((367,ny,nx),np.nan); clim=np.full((367,ny,nx),np.nan)
for dd in range(1,367):
    if dd==60: continue
    bdates=[i for i in bl_idx if doy_ext[i]==dd]
    if not bdates: continue
    pidx=set()
    for b in bdates:
        for k in range(-5,6):
            j=b+k
            if 0<=j<len(ext): pidx.add(j)
    pool=SST_b[sorted(pidx)]
    thr[dd]=np.nanquantile(pool,0.9,axis=0,method='hazen')
    clim[dd]=np.nanmean(pool,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(x):
    base=x[1:367]
    out=np.empty_like(base)
    for i in range(366):
        ids=[(i+k)%366 for k in range(-15,16)]
        out[i]=np.mean(base[ids],axis=0)
    return out
thr366=smooth(thr)
tdoy=doy(tdays)
thr_t=thr366[tdoy-1]
sea=np.all(np.isfinite(T),axis=0)
print('sea cells',sea.sum(),'thr nan in sea',np.isnan(thr_t[:,sea]).sum())
hot=(T>=thr_t)&sea[None]
nT=T.shape[0]
mhw_cell=np.zeros((nT,ny,nx),bool)
for iy,ix in zip(*np.where(sea)):
    h=hot[:,iy,ix]
    runs=[];s=None
    for t in range(nT+1):
        v=h[t] if t<nT else False
        if v and s is None: s=t
        if not v and s is not None:
            if t-s>=5: runs.append([s,t-1])
            s=None
    merged=[]
    for r in runs:
        if merged and r[0]-merged[-1][1]-1 in (1,2): merged[-1][1]=r[1]
        else: merged.append(list(r))
    for s_,e_ in merged: mhw_cell[s_:e_+1,iy,ix]=True
active=mhw_cell.reshape(nT,-1).any(axis=1)
events=[];s=None
for t in range(nT+1):
    v=active[t] if t<nT else False
    if v and s is None: s=t
    if not v and s is not None:
        events.append({"onset":str(tdays[s].date()),"end":str(tdays[t-1].date())}); s=None
print(events, 'cell-days', mhw_cell.sum(), 'active', active.sum())
os.makedirs('output',exist_ok=True)
ds_out=xr.Dataset({'mhw':(('time','lat','lon'),mhw_cell.astype(np.uint8))},
    coords={'time':tdays.values,'lat':lat,'lon':lon})
ds_out['mhw'].attrs={'long_name':'marine heatwave mask'}
ds_out.to_netcdf('output/mhw_mask.nc',engine='h5netcdf')
report={"region":{"lat_min":64.39,"lat_max":65.59,"lon_min":23.41,"lon_max":24.61},
 "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
 "target_analysed":{"start":"2019-06-01","end":"2019-08-31"},
 "events":events,"complete":True,
 "caveats":"Analysed grid cells lat 64.40-65.58, lon 23.42-24.60 (60x60); 3311 cells are sea over the whole target period, others are 0 in the mask. Baseline pools include the allowed extension days 1991-12-27..31 and 2003-01-01..05. Computed in float64 from float32 SST as stored (kelvin)."}
json.dump(report,open('output/report.json','w'),indent=1)
chk=xr.open_dataset('output/mhw_mask.nc',engine='h5netcdf')
print(chk.mhw.dims, chk.mhw.shape, chk.mhw.dtype, int(chk.mhw.sum()))
'''
open('/tmp/run.py','w').write(script)
import subprocess
r=subprocess.run(['python','/tmp/run.py'],capture_output=True,text=True,cwd='/tmp')
print(r.stdout, r.stderr[-2000:])
