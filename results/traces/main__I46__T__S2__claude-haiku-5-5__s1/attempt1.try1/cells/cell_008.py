
script = r'''
import numpy as np, xarray as xr, json, os, warnings, datetime as dt
warnings.filterwarnings('ignore')
os.makedirs('/tmp/w',exist_ok=True); os.makedirs('output',exist_ok=True)
c=np.load('/tmp/w/cache.npz')
xb,tb,xt,tt,latv,lonv=c['xb'],c['tb'],c['xt'],c['tt'],c['lat'],c['lon']
base=lambda s: np.datetime64(s)
tb=tb.astype('datetime64[D]'); tt=tt.astype('datetime64[D]')
# day-of-year: calendar fixed, Feb29=60
def doy(d):
    d=d.astype(dt.date) if False else d
    y=int(str(d)[:4]); m=int(str(d)[5:7]); dd=int(str(d)[8:10])
    cum=[0,31,59,90,120,151,181,212,243,273,304,334]  # non-leap month starts (Mar onward shifted by leap)
    # define: Jan..Feb as usual, Feb29=60, Mar1=61
    if m==1: return dd
    if m==2: return 31+dd
    days_before=[0,31,59,90,120,151,181,212,243,273,304,334]
    return days_before[m-1]+dd+1
# check: Mar1 -> 59+1+1=61 ; Dec31 -> 334+31+1=366
assert doy(np.datetime64('2001-03-01'))==61 and doy(np.datetime64('2001-02-28'))==59 and doy(np.datetime64('2000-02-29'))==60 and doy(np.datetime64('2001-12-31'))==366
# baseline date index mapping
dates=tb
idx_of={str(d):i for i,d in enumerate(dates)}
bl0=np.datetime64('1992-01-01'); bl1=np.datetime64('2002-12-31')
pool_idx={}
for i,d in enumerate(dates):
    if d<bl0 or d>bl1: continue
    k=doy(d)
    if k==60: continue
    pool_idx.setdefault(k,set())
    for off in range(-5,6):
        dd=d+np.timedelta64(off,'D')
        j=idx_of.get(str(dd))
        if j is None: raise SystemExit('missing padded date')
        pool_idx[k].add(j)
ny,nx=latv.size,lonv.size
thr=np.full((367,)+xb.shape[1:],np.nan)
clim=np.full((367,)+xb.shape[1:],np.nan)
for k in range(1,367):
    if k==60: continue
    ii=np.array(sorted(pool_idx[k]))
    sub=xb[ii]
    thr[k]=np.nanquantile(sub,0.9,axis=0,method='hazen')
    clim[k]=np.nanmean(sub,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    a1=a[1:367]  # 366 days, index 0 = day1
    out=np.empty_like(a1)
    for d in range(366):
        ids=[(d+o)%366 for o in range(-15,16)]
        out[d]=np.mean(a1[ids],axis=0)
    return out
thr366=smooth(thr); clim366=smooth(clim)
# sea cells
sea=np.all(np.isfinite(xt),axis=0)
print('sea cells',sea.sum(),'of',sea.size)
# hot days
tdoy=np.array([doy(d) for d in tt])
T=thr366[tdoy-1]  # (92,ny,nx)
hot=(xt>=T)&sea[None]
mhw=np.zeros_like(hot)
def runs(b):
    # return list of (s,e) inclusive for True runs
    out=[];n=len(b);i=0
    while i<n:
        if b[i]:
            j=i
            while j+1<n and b[j+1]: j+=1
            out.append((i,j)); i=j+1
        else: i+=1
    return out
for a in range(ny):
    for o in range(nx):
        if not sea[a,o]: continue
        h=hot[:,a,o]
        segs=[s for s in runs(h) if s[1]-s[0]+1>=5]
        merged=[]
        for s in segs:
            if merged and s[0]-merged[-1][1]-1<=2:
                merged[-1]=(merged[-1][0],s[1])
            else: merged.append(s)
        for s,e in merged: mhw[s:e+1,a,o]=True
active=mhw.any(axis=(1,2))
ev=[]
for s,e in runs(active):
    ev.append({'onset':str(tt[s]),'end':str(tt[e])})
print('events',ev)
print('hot cells-days',hot.sum(),'mhw cell-days',mhw.sum())
ds=xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype(np.uint8))},
   coords={'time':tt.astype('datetime64[ns]'),'lat':latv.astype(np.float32),'lon':lonv.astype(np.float32)})
ds['mhw'].attrs={'long_name':'marine heatwave flag per cell'}
ds.to_netcdf('output/mhw_mask.nc')
rep={'region':{'lat_min':64.39,'lat_max':65.59,'lon_min':23.41,'lon_max':24.61},
 'baseline_analysed':{'start':'1992-01-01','end':'2002-12-31'},
 'target_analysed':{'start':str(tt[0]),'end':str(tt[-1])},
 'events':ev,'complete':True,
 'caveats':'Region grid is 60x60 cells (lat 64.40-65.58, lon 23.42-24.60) as stored; sea cells = finite on all target days. Pool uses set-union of +-5-day windows (each date once). Land cells 0.'}
json.dump(rep,open('output/report.json','w'),indent=1)
print(json.dumps(rep)[:1500])
'''
open('/tmp/w/analyze.py','w').write(script)
import subprocess
r=subprocess.run(['python','/tmp/w/analyze.py'],capture_output=True,text=True,cwd='/tmp/w')
print(r.stdout[-6000:], r.stderr[-3000:])
