
ny,nx=sst.shape[1:]
thr=np.full((367,ny,nx),np.nan); clim=np.full((367,ny,nx),np.nan)
for d in range(1,367):
    if d==60: continue
    P_=sst[pool_idx[d]]  # (n,ny,nx)
    with np.errstate(all='ignore'):
        thr[d]=np.nanquantile(P_,0.9,axis=0,method='hazen')
        clim[d]=np.nanmean(P_,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):  # a: (366,...) days 1..366 stored at index 1..366 -> use 0-based
    out=np.empty_like(a)
    base=a[1:367]
    for k in range(366):
        ii=[(k+j)%366 for j in range(-15,16)]
        out[k+1]=np.mean(base[ii],axis=0)
    return out
thr_s=smooth(thr); clim_s=smooth(clim)
print(np.isnan(thr_s[1:]).sum(), np.isnan(clim_s[1:]).sum(), np.isnan(thr_s[1:]).all(axis=0).sum())
# target
tmask=np.array([dt.date(2017,6,1)<=d<=dt.date(2017,8,31) for d in dates])
tgt_dates=[d for d,m in zip(dates,tmask) if m]; print(len(tgt_dates), tgt_dates[0], tgt_dates[-1])
T=sst[tmask]  # (92,ny,nx)
sea=np.all(np.isfinite(T),axis=0)
print('sea cells', sea.sum(), 'of', sea.size)
