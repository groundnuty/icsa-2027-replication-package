code='''
import numpy as np,pandas as pd,json,os,xarray as xr
from scipy.ndimage import label
def doy(dt):
    m,d=dt.month,dt.day
    return (pd.Timestamp(2000,m,d).dayofyear)
A=pd.date_range('1991-12-27','2003-01-05')
X=np.stack([np.load(f'cache/{x:%Y%m%d}.npy') for x in A]).astype(np.float64)
T=pd.date_range('2010-06-01','2010-08-31')
Y=np.stack([np.load(f'cache/{x:%Y%m%d}.npy') for x in T]).astype(np.float64)
import fsspec
fs=fsspec.filesystem('onedata')
d0=xr.open_dataset(fs.open('icsa2027_data_20261101T090944Z/s1z/sst_20100601.nc','rb'),engine='h5netcdf').sel(latitude=slice(56.62,57.84),longitude=slice(20.22,21.44))
lat=d0.latitude.values;lon=d0.longitude.values
la=(lat>=56.63-1e-4)&(lat<=57.83+1e-4);lo=(lon>=20.23-1e-4)&(lon<=21.43+1e-4)
print(lat[la][[0,-1]],lon[lo][[0,-1]],la.sum(),lo.sum())
X=X[:,la][:,:,lo];Y=Y[:,la][:,:,lo];lat=lat[la];lon=lon[lo]
sea=np.isfinite(Y).all(0);print(sea.sum(),sea.size)
doys=np.array([doy(x) for x in A])
base=(A>=pd.Timestamp('1992-01-01'))&(A<=pd.Timestamp('2002-12-31'))
ny,nx=sea.shape
thr=np.full((366,ny,nx),np.nan);clim=thr.copy()
for d in range(1,367):
    if d==60:continue
    idx=set()
    for i in np.where(base&(doys==d))[0]:
        idx.update(range(i-5,i+6))
    idx=sorted(i for i in idx if 0<=i<len(A))
    P=X[idx]
    thr[d-1]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim[d-1]=np.nanmean(P,axis=0)
for a in (thr,clim):
    a[59]=(a[58]+a[60])/2
def sm(a):
    return sum(np.roll(a,-k,axis=0) for k in range(-15,16))/31
thr=sm(thr)
td=np.array([doy(x) for x in T])
hot=Y>=thr[td-1]
hot&=sea
nt=len(T);mhw=np.zeros_like(hot)
for i in range(ny):
  for j in range(nx):
    if not sea[i,j]:continue
    h=hot[:,i,j].copy()
    lab,n=label(h)
    runs=[(np.where(lab==k)[0][0],np.where(lab==k)[0][-1]) for k in range(1,n+1)]
    runs=[r for r in runs if r[1]-r[0]+1>=5]
    m=np.zeros(nt,bool);prev=None
    for s,e in runs:
        m[s:e+1]=True
        if prev is not None and s-prev-1<=2:m[prev+1:s]=True
        prev=e
    mhw[:,i,j]=m
act=mhw.any((1,2))
ev=[];s=None
for k in range(nt):
    if act[k] and s is None:s=k
    if (not act[k]) and s is not None:ev.append((s,k-1));s=None
if s is not None:ev.append((s,nt-1))
f=lambda k:T[k].strftime('%Y-%m-%d')
events=[{"onset":f(a),"end":f(b)} for a,b in ev];print(events,mhw.sum())
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype(np.uint8))},coords={'time':T,'lat':lat,'lon':lon}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":56.63,"lat_max":57.83,"lon_min":20.23,"lon_max":21.43},
"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
"target_analysed":{"start":"2010-06-01","end":"2010-08-31"},
"events":events,"complete":True,"caveats":""},open('output/report.json','w'))
'''
open('an.py','w').write(code)
import subprocess
r=subprocess.run(['python','an.py'],capture_output=True,text=True);print(r.stdout,r.stderr[-1500:])