
import fsspec,xarray as xr,numpy as np,pandas as pd,os,json
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds=xr.open_dataset(fs.open(p,'rb'),engine='h5netcdf')
la=ds.latitude.values;lo=ds.longitude.values
li=np.where((la>=56.13-1e-4)&(la<=57.33+1e-4))[0];oi=np.where((lo>=17.71-1e-4)&(lo<=18.91+1e-4))[0]
sub=ds.analysed_sst.isel(latitude=slice(li[0],li[-1]+1),longitude=slice(oi[0],oi[-1]+1))
t=ds.time.values
i0=np.searchsorted(t,np.datetime64('1991-12-27'));i1=np.searchsorted(t,np.datetime64('2003-01-06'))
B=sub.isel(time=slice(i0,i1)).values.astype('float64')
j0=np.searchsorted(t,np.datetime64('2019-06-01'));j1=np.searchsorted(t,np.datetime64('2019-09-01'))
T=sub.isel(time=slice(j0,j1)).values.astype('float64')
dt=pd.DatetimeIndex(t[i0:i1]); assert (np.diff(dt.values)==np.timedelta64(1,'D')).all()
def doy(x): return np.asarray(x.dayofyear + ((~x.is_leap_year)&(x.month>2)))
dd=doy(dt)
cen=np.where((dt>='1992-01-01')&(dt<='2002-12-31'))[0]
thr=np.full((367,60,60),np.nan);clm=thr.copy()
for d in range(1,367):
    if d==60: continue
    idx=set()
    for c in cen[dd[cen]==d]:
        idx.update(range(max(c-5,0),min(c+5,len(dt)-1)+1))
    P=B[sorted(idx)]
    with np.errstate(all='ignore'):
        thr[d]=np.nanquantile(P,0.9,axis=0,method='hazen');clm[d]=np.nanmean(P,0)
thr[60]=(thr[59]+thr[61])/2
def sm(a):
    a=a[1:]; return np.mean([np.roll(a,-k,0) for k in range(-15,16)],0)
ths=sm(thr)
td=pd.DatetimeIndex(t[j0:j1]);tdd=doy(td)
sea=np.isfinite(T).all(0)
hot=(T>=ths[tdd-1])&sea
mh=np.zeros(hot.shape,bool);n=len(td)
for i in range(60):
  for j in range(60):
    if not sea[i,j]: continue
    h=hot[:,i,j];runs=[];s=None
    for k in range(n+1):
        if k<n and h[k]:
            if s is None:s=k
        elif s is not None:
            if k-s>=5:runs.append([s,k-1])
            s=None
    m=[]
    for r in runs:
        if m and r[0]-m[-1][1]-1<=2:m[-1][1]=r[1]
        else:m.append(r)
    for a,b in m:mh[a:b+1,i,j]=1
act=mh.any((1,2));ev=[];s=None
for k in range(n+1):
    if k<n and act[k]:
        if s is None:s=k
    elif s is not None:ev.append({"onset":str(td[s].date()),"end":str(td[k-1].date())});s=None
print(sea.sum(),ev)
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),mh.astype('uint8'))},coords={'time':td,'lat':la[li],'lon':lo[oi]}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":56.13,"lat_max":57.33,"lon_min":17.71,"lon_max":18.91},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2019-06-01","end":"2019-08-31"},"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))
