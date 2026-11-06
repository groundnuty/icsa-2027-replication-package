
import xarray as xr,numpy as np,pandas as pd,json,os,warnings
warnings.filterwarnings('ignore')
from scipy.ndimage import label
b=xr.open_dataarray('/tmp/b.nc');t=xr.open_dataarray('/tmp/t.nc')
bt=pd.DatetimeIndex(b.time.values);B=b.values.astype('float64')
def doy(i): return np.array([pd.Timestamp(2000,x.month,x.day).day_of_year for x in i])
bd=doy(bt)
core=np.where((bt>='1992-01-01')&(bt<='2002-12-31'))[0]
ny,nx=B.shape[1:]
thr=np.full((366,ny,nx),np.nan);clim=thr.copy()
for d in range(1,367):
    if d==60: continue
    idx=set()
    for i in core[bd[core]==d]: idx.update(range(i-5,i+6))
    idx=sorted(j for j in idx if 0<=j<len(bt))
    P=B[idx]
    thr[d-1]=np.nanquantile(P,0.9,axis=0,method='hazen');clim[d-1]=np.nanmean(P,axis=0)
thr[59]=(thr[58]+thr[60])/2
thr=sum(np.roll(thr,-k,axis=0) for k in range(-15,16))/31
T=t.values.astype('float64');tt=pd.DatetimeIndex(t.time.values);td=doy(tt)
sea=np.isfinite(T).all(0)
hot=(T>=thr[td-1])&sea
out=np.zeros(hot.shape,bool)
for i in range(ny):
  for j in range(nx):
    if not sea[i,j]: continue
    lab,n=label(hot[:,i,j])
    runs=[]
    for k in range(1,n+1):
        w=np.where(lab==k)[0]
        if len(w)>=5: runs.append((w[0],w[-1]))
    for k,(s,e) in enumerate(runs):
        out[s:e+1,i,j]=True
        if k+1<len(runs) and runs[k+1][0]-e-1<=2: out[e:runs[k+1][0],i,j]=True
act=out.any((1,2));lab,n=label(act)
ev=[{"onset":str(tt[np.where(lab==k)[0][0]].date()),"end":str(tt[np.where(lab==k)[0][-1]].date())} for k in range(1,n+1)]
print(sea.sum(),ev)
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),out.astype('uint8'))},coords={'time':t.time.values,'lat':t.latitude.values,'lon':t.longitude.values}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":56.63,"lat_max":57.83,"lon_min":20.23,"lon_max":21.43},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2008-06-01","end":"2008-08-31"},"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))
