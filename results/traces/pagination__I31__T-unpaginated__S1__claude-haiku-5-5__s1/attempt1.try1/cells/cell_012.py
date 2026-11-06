
code = r'''
import numpy as np, datetime as dt, json, os
import xarray as xr
Z=np.load('work/sst.npz')
sst=Z['sst']; dates=[dt.date.fromisoformat(s) for s in Z['dates']]; lat=Z['lat']; lon=Z['lon']
idx={d:i for i,d in enumerate(dates)}
cum=[0,31,60,91,121,152,182,213,244,274,305,335]
def doy(d):
    if d.month==2 and d.day==29: return 60
    return cum[d.month-1]+d.day
bl=[dt.date(1992,1,1)+dt.timedelta(days=i) for i in range((dt.date(2002,12,31)-dt.date(1992,1,1)).days+1)]
pool_idx={d:set() for d in range(1,367)}
for b in bl:
    dd=doy(b)
    if dd==60: continue
    pool_idx[dd].update(idx[b+dt.timedelta(days=k)] for k in range(-5,6))
pool_idx={d:sorted(v) for d,v in pool_idx.items()}
ny,nx=sst.shape[1:]
thr=np.full((367,ny,nx),np.nan); clim=np.full((367,ny,nx),np.nan)
for d in range(1,367):
    if d==60: continue
    P_=sst[pool_idx[d]]
    with np.errstate(all='ignore'):
        thr[d]=np.nanquantile(P_,0.9,axis=0,method='hazen')
        clim[d]=np.nanmean(P_,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    out=np.full_like(a,np.nan)
    base=a[1:367]
    for k in range(366):
        ii=[(k+j)%366 for j in range(-15,16)]
        out[k+1]=np.mean(base[ii],axis=0)
    return out
thr_s=smooth(thr); clim_s=smooth(clim)
print('nan thr days/cells', np.isnan(thr_s[1:]).sum(), 'nan clim', np.isnan(clim_s[1:]).sum())
tmask=np.array([dt.date(2017,6,1)<=d<=dt.date(2017,8,31) for d in dates])
tgt=[d for d,m in zip(dates,tmask) if m]
print(len(tgt), tgt[0], tgt[-1])
T=sst[tmask]
sea=np.all(np.isfinite(T),axis=0)
print('sea cells', sea.sum(), 'of', sea.size)
tdoy=np.array([doy(d) for d in tgt])
TH=thr_s[tdoy]  # (92,ny,nx)
with np.errstate(invalid='ignore'):
    hot=(T>=TH)&sea[None]
# per-cell runs
N=len(tgt)
mhw=np.zeros((N,ny,nx),bool)
for i in range(ny):
    for j in range(nx):
        if not sea[i,j]: continue
        h=hot[:,i,j]
        # runs
        runs=[]; k=0
        while k<N:
            if h[k]:
                s=k
                while k<N and h[k]: k+=1
                if k-s>=5: runs.append([s,k-1])
            else: k+=1
        # join gaps of 1-2 non-hot days
        merged=[]
        for r in runs:
            if merged and r[0]-merged[-1][1]-1 <= 2 and r[0]-merged[-1][1]-1>=1:
                merged[-1][1]=r[1]
            else: merged.append(list(r))
        for s,e in merged: mhw[s:e+1,i,j]=True
active=mhw.any(axis=(1,2))
events=[]; k=0
while k<N:
    if active[k]:
        s=k
        while k<N and active[k]: k+=1
        events.append((tgt[s].isoformat(), tgt[k-1].isoformat()))
    else: k+=1
print('events', events)
print('hot cells-days', hot.sum(), 'mhw cell-days', mhw.sum(), 'active days', active.sum())
os.makedirs('output',exist_ok=True)
ds=xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype(np.uint8))},
    coords={'time':np.array([np.datetime64(d.isoformat()) for d in tgt],dtype='datetime64[ns]'),'lat':lat.astype(np.float64),'lon':lon.astype(np.float64)})
ds['mhw'].attrs={'long_name':'marine heatwave per-cell flag'}
ds.to_netcdf('output/mhw_mask.nc')
rep={'region':{'lat_min':58.69,'lat_max':59.89,'lon_min':18.69,'lon_max':19.89},
     'baseline_analysed':{'start':'1992-01-01','end':'2002-12-31'},
     'target_analysed':{'start':tgt[0].isoformat(),'end':tgt[-1].isoformat()},
     'events':[{'onset':a,'end':b} for a,b in events],
     'complete':True,
     'caveats':'Sea cells defined as finite on all target days; land/partially-missing cells set to 0. Baseline pool windows use actual dates (1991-12-27..2003-01-05 reached by windows). Lat/lon coords are the dataset grid values (58.70-59.88, 18.70-19.88) because grid points lie inside the inclusive bounds.'}
json.dump(rep,open('output/report.json','w'),indent=2)
print(json.dumps(rep)[:1500])
'''
os.makedirs('work',exist_ok=True) if False else None
import os; os.makedirs('work',exist_ok=True)
open('work/compute.py','w').write(code)
import subprocess
r=subprocess.run(['python','work/compute.py'],capture_output=True,text=True); print(r.stdout[-6000:], r.stderr[-3000:])
