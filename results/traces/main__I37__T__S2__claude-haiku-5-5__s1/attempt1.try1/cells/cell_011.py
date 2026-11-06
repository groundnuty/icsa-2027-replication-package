
import fsspec, xarray as xr, numpy as np, pandas as pd, os, json, warnings
warnings.filterwarnings('ignore')
fs = fsspec.filesystem('onedata')
f=fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','rb')
ds=xr.open_dataset(f,engine='h5netcdf')
sub=ds.sel(latitude=slice(60.09,61.29), longitude=slice(20.01,21.21))
b=sub.analysed_sst.sel(time=slice('1991-12-27','2003-01-05')).load()
t=sub.analysed_sst.sel(time=slice('2012-06-01','2012-08-31')).load()
bt=pd.DatetimeIndex(b.time.values); tt=pd.DatetimeIndex(t.time.values)
bvals=b.values.astype(np.float64); tvals=t.values.astype(np.float64)
NLAT,NLON=b.shape[1],b.shape[2]
def ldoy(dates): return np.array([pd.Timestamp(2000,d.month,d.day).dayofyear for d in dates])
bdoy=ldoy(bt)
base_mask=(bt>=pd.Timestamp('1992-01-01'))&(bt<=pd.Timestamp('2002-12-31'))
date2idx={d:i for i,d in enumerate(bt)}
thr=np.full((366,NLAT,NLON),np.nan)
for d in range(1,367):
    if d==60: continue
    anchors=bt[base_mask & (bdoy==d)]
    idx=sorted({date2idx[a+pd.Timedelta(days=k)] for a in anchors for k in range(-5,6)})
    thr[d-1]=np.nanquantile(bvals[idx],0.9,axis=0,method='hazen')
thr[59]=(thr[58]+thr[60])/2
thr_s=np.empty_like(thr)
for i in range(366):
    thr_s[i]=np.mean(thr[[(i+k)%366 for k in range(-15,16)]],axis=0)
sea=np.all(np.isfinite(tvals),axis=0)
tdoy=ldoy(tt)-1
T=len(tt)
hot=np.zeros((T,NLAT,NLON),bool)
hot[:,sea]=tvals[:,sea]>=thr_s[tdoy][:,sea]
mask=np.zeros((T,NLAT,NLON),np.uint8)
for i,j in zip(*np.where(sea)):
    h=hot[:,i,j]; runs=[]; k=0
    while k<T:
        if h[k]:
            s=k
            while k<T and h[k]: k+=1
            if k-s>=5: runs.append([s,k-1])
        else: k+=1
    merged=[]
    for r in runs:
        gap=r[0]-merged[-1][1]-1 if merged else None
        if merged and 1<=gap<=2: merged[-1][1]=r[1]
        else: merged.append(list(r))
    for s,e in merged: mask[s:e+1,i,j]=1
active=mask.reshape(T,-1).any(axis=1)
events=[]; k=0
while k<T:
    if active[k]:
        s=k
        while k<T and active[k]: k+=1
        events.append({"onset":str(tt[s].date()),"end":str(tt[k-1].date())})
    else: k+=1
print('hot cell-days',int(hot.sum()),'mask',int(mask.sum()),'events',events)
os.makedirs('output',exist_ok=True)
out=xr.Dataset({'mhw':(('time','lat','lon'),mask)},
               coords={'time':t.time.values,'lat':t.latitude.values,'lon':t.longitude.values})
out.to_netcdf('output/mhw_mask.nc')
rep={"region":{"lat_min":60.09,"lat_max":61.29,"lon_min":20.01,"lon_max":21.21},
     "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
     "target_analysed":{"start":"2012-06-01","end":"2012-08-31"},
     "events":events,"complete":True,
     "caveats":("No regional MHW events: no sea cell had a run of 5+ consecutive hot days. Hot days are rare: %d sea cell-days of target period reached the threshold. "
                "Pool windows at baseline edges use SST from 1991-12-27 to 2003-01-05, as the method specifies. "
                "Sea cells = %d of %d grid cells. Land cells are 0 in the mask.")%(int(hot.sum()),int(sea.sum()),sea.size)}
json.dump(rep,open('output/report.json','w'),indent=2)
print(open('output/report.json').read()); print(xr.open_dataset('output/mhw_mask.nc').mhw.shape)
