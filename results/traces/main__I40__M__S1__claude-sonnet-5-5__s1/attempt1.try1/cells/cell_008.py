import os,json,numpy as np,pandas as pd,xarray as xr
d='/data/icsa2027_data_20261101T090944Z/s1z'
ds=xr.open_dataset(d+'/sst_20090601.nc',engine='h5netcdf')
lat=ds.latitude.values;lon=ds.longitude.values
li=np.where((lat>=61.57-1e-4)&(lat<=62.77+1e-4))[0];lj=np.where((lon>=20.17-1e-4)&(lon<=21.37+1e-4))[0]
B=np.load('/tmp/B.npy');T=np.load('/tmp/T.npy')
dates=pd.date_range('1991-12-27','2003-01-05');td=pd.date_range('2009-06-01','2009-08-31')
def doy(ix):
    return np.array([ (pd.Timestamp(2000,m,dd).dayofyear) for m,dd in zip(ix.month,ix.day)])
dd=doy(dates)
base=np.where((dates>='1992-01-01')&(dates<='2002-12-31'))[0]
ny,nx=B.shape[1:]
thr=np.full((366,ny,nx),np.nan);clim=thr.copy()
for D in range(1,367):
    if D==60: continue
    idx=set()
    for b in base[dd[base]==D]:
        idx.update(range(b-5,b+6))
    idx=sorted(i for i in idx if 0<=i<len(dates))
    P=B[idx]
    thr[D-1]=np.nanquantile(P,0.9,axis=0,method='hazen');clim[D-1]=np.nanmean(P,axis=0)
for a in (thr,clim): a[59]=(a[58]+a[60])/2
def sm(a):
    return sum(np.roll(a,s,axis=0) for s in range(-15,16))/31
thr=sm(thr)
sea=np.isfinite(T).all(0)
dt=doy(td)
hot=(T>=thr[dt-1])&sea
nt=len(td);mhw=np.zeros_like(hot)
for i in range(ny):
  for j in range(nx):
    if not sea[i,j]: continue
    h=hot[:,i,j];runs=[];k=0
    while k<nt:
        if h[k]:
            e=k
            while e+1<nt and h[e+1]:e+=1
            if e-k+1>=5:runs.append([k,e])
            k=e+1
        else:k+=1
    m=[]
    for r in runs:
        if m and r[0]-m[-1][1]-1<=2:m[-1][1]=r[1]
        else:m.append(r)
    for a,b in m:mhw[a:b+1,i,j]=True
act=mhw.any((1,2))
ev=[];k=0
while k<nt:
    if act[k]:
        e=k
        while e+1<nt and act[e+1]:e+=1
        ev.append({"onset":str(td[k].date()),"end":str(td[e].date())});k=e+1
    else:k+=1
print(sea.sum(),ev,mhw.sum())
os.makedirs('output',exist_ok=True)
o=xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype('uint8'))},coords={'time':td,'lat':lat[li],'lon':lon[lj]})
o.to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":61.57,"lat_max":62.77,"lon_min":20.17,"lon_max":21.37},
"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
"target_analysed":{"start":"2009-06-01","end":"2009-08-31"},
"events":ev,"complete":True,"caveats":"Baseline pools also used 1991-12-27..31 and 2003-01-01..05 as specified."},open('output/report.json','w'))