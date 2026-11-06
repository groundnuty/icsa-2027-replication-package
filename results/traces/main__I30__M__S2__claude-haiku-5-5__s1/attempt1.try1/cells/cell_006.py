
import json, os
os.makedirs('output',exist_ok=True)
lat=sub.latitude.values; lon=sub.longitude.values
# doy table via leap year 2000
ref=pd.date_range('2000-01-01','2000-12-31')
doy_of_md={(d.month,d.day):i+1 for i,d in enumerate(ref)}
def doy(ts): return doy_of_md[(ts.month,ts.day)]
bdates=pd.date_range('1991-12-27','2003-01-05')
bvals=b.values.astype(np.float64)  # (T,lat,lon)
bidx={d:i for i,d in enumerate(bdates)}
base_start=pd.Timestamp('1992-01-01'); base_end=pd.Timestamp('2002-12-31')
bl=pd.date_range(base_start,base_end)
pool_idx={d:set() for d in range(1,367)}
for bd in bl:
    dd=doy(bd)
    if dd==60: continue
    for k in range(-5,6):
        pool_idx[dd].add(bidx[bd+pd.Timedelta(days=k)])
thr=np.full((367,)+bvals.shape[1:],np.nan); clim=np.full_like(thr,np.nan)
import warnings; warnings.filterwarnings('ignore')
for d in range(1,367):
    if d==60: continue
    idx=sorted(pool_idx[d])
    P=bvals[idx]
    thr[d]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim[d]=np.nanmean(P,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(A):  # A indexed 1..366 in [1..366]
    arr=A[1:367]  # 366 elements
    out=np.empty_like(arr)
    for i in range(366):
        ids=[(i+k)%366 for k in range(-15,16)]
        out[i]=np.mean(arr[ids],axis=0)
    return out
T=smooth(thr); C=smooth(clim)  # index i -> doy i+1
print(T.shape, np.isnan(T).sum(), np.isnan(C).sum())
# baseline dates range used
print(len(pool_idx[1]), len(pool_idx[366]))
