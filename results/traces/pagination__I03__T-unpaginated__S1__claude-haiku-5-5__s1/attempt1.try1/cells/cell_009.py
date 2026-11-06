
code = r'''
import numpy as np, json, os, warnings, xarray as xr
warnings.filterwarnings('ignore')
z=np.load('/tmp/sst.npz')
sst=z['sst']; lat=z['lat']; lon=z['lon']; alld=z['dates'].astype('datetime64[D]')
ndays,nla,nlo=sst.shape
D=lambda s: np.datetime64(s)
def doy2(d):
    d=np.datetime64(d,'D')
    lm=int(str(d)[5:7]); dd=int(str(d)[8:10])
    return int((np.datetime64('2000-%02d-%02d'%(lm,dd))-np.datetime64('2000-01-01')).astype(int))+1
base_lo,base_hi=D('1992-01-01'),D('2002-12-31')
idx_of={str(d):i for i,d in enumerate(alld)}
pools={d:set() for d in range(1,367) if d!=60}
bdates=np.arange(base_lo,base_hi+np.timedelta64(1,'D'))
for b in bdates:
    dd=doy2(b)
    if dd==60: continue
    for off in range(-5,6):
        pools[dd].add(idx_of[str(b+np.timedelta64(off,'D'))])
thr=np.full((367,nla,nlo),np.nan); clim=np.full((367,nla,nlo),np.nan)
for dd in pools:
    ii=sorted(pools[dd]); arr=sst[ii]
    thr[dd]=np.nanquantile(arr,0.9,axis=0,method='hazen')
    clim[dd]=np.nanmean(arr,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    b=a[1:367]; out=np.zeros_like(b)
    for k in range(-15,16): out+=np.roll(b,-k,axis=0)
    out/=31
    res=np.full_like(a,np.nan); res[1:367]=out; return res
thr_s=smooth(thr)
tidx=np.array([i for i,d in enumerate(alld) if '2014-06-01'<=str(d)<='2014-08-31'])
tsst=sst[tidx]; tdates_=alld[tidx]
sea=np.isfinite(tsst).all(axis=0)
print('target days',len(tidx), tdates_[0], tdates_[-1],'sea cells',sea.sum())
doys=np.array([doy2(d) for d in tdates_])
T=thr_s[doys]
hot=(tsst>=T)&sea[None]
mhw=np.zeros_like(hot)
def runs(b):
    r=[]; n=len(b); i=0
    while i<n:
        if b[i]:
            j=i
            while j+1<n and b[j+1]: j+=1
            r.append([i,j]); i=j+1
        else: i+=1
    return r
for a in range(nla):
    for c in range(nlo):
        if not sea[a,c]: continue
        rr=[x for x in runs(hot[:,a,c]) if x[1]-x[0]+1>=5]
        if not rr: continue
        merged=[rr[0][:]]
        for s,e in rr[1:]:
            if s-merged[-1][1]-1<=2: merged[-1][1]=e
            else: merged.append([s,e])
        for s,e in merged: mhw[s:e+1,a,c]=True
active=mhw.any(axis=(1,2))
events=[]; i=0; n=len(active)
while i<n:
    if active[i]:
        j=i
        while j+1<n and active[j+1]: j+=1
        events.append((str(tdates_[i]),str(tdates_[j]))); i=j+1
    else: i+=1
print('events',events, 'mhw cell-days', mhw.sum())
os.makedirs('output',exist_ok=True)
da=xr.DataArray(mhw.astype(np.uint8), dims=('time','lat','lon'),
    coords={'time':tdates_.astype('datetime64[ns]'),'lat':lat,'lon':lon}, name='mhw')
xr.Dataset({'mhw':da}).to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
rep={
 'region':{'lat_min':54.17,'lat_max':55.37,'lon_min':13.25,'lon_max':14.45},
 'baseline_analysed':{'start':'1992-01-01','end':'2002-12-31'},
 'target_analysed':{'start':'2014-06-01','end':'2014-08-31'},
 'events':[{'onset':s,'end':e} for s,e in events],
 'complete':True,
 'caveats':'Grid of 60x60 cells (lat 54.18-55.36, lon 13.26-14.44). 3303 of 3600 cells are sea cells (finite on all target days); other cells are 0 in mask. Pools use dates within +/-5 days of 1992-2002 baseline dates, including the extra 1991-12-27 to 2003-01-05 window days. Day 60 set to mean of days 59 and 61 before smoothing. Hot runs and gap joining were computed within the target period only.'
}
json.dump(rep,open('output/report.json','w'),indent=2)
print(xr.open_dataset('output/mhw_mask.nc').mhw.shape)
'''
open('/tmp/run.py','w').write(code)
import subprocess
r=subprocess.run(['python','/tmp/run.py'],capture_output=True,text=True,cwd='/tmp')
print(r.stdout, r.stderr[-2000:])
