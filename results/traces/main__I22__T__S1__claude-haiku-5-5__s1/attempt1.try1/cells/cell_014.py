
thr_raw=np.full((367,len(LAT),len(LON)),np.nan); clim_raw=np.full((367,len(LAT),len(LON)),np.nan)
import warnings; warnings.filterwarnings('ignore')
for k in range(1,367):
    if k==60: continue
    ii=[idx[t] for t in sorted(pool_dates[k]) if t in idx]
    P=cube[ii]  # (n,lat,lon)
    thr_raw[k]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim_raw[k]=np.nanmean(P,axis=0)
thr_raw[60]=(thr_raw[59]+thr_raw[61])/2
clim_raw[60]=(clim_raw[59]+clim_raw[61])/2
A_thr=thr_raw[1:]; A_clim=clim_raw[1:]   # 366 arrays, index d-1
def smooth(A):
    out=np.empty_like(A)
    for d in range(366):
        ids=[(d+o)%366 for o in range(-15,16)]
        out[d]=A[ids].mean(axis=0)
    return out
thr=smooth(A_thr); clim=smooth(A_clim)
print('nan thr sea cells', np.isnan(thr[:,sea]).sum(), 'nan clim sea', np.isnan(clim[:,sea]).sum())
print(thr[[151,152,242]][:,sea][:,:3], clim[[151]][:,sea][:,:3])
