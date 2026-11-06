
ny,nx=S.shape[1:]
thr=np.full((367,ny,nx),np.nan); clim=np.full((367,ny,nx),np.nan)
for dd,idx in pool_idx.items():
    P=Sb[idx]  # (121,ny,nx)
    thr[dd]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim[dd]=np.nanmean(P,axis=0)
thr=thr[1:367]; clim=clim[1:367]  # index 0 -> doy1
thr[59]=(thr[58]+thr[60])/2; clim[59]=(clim[58]+clim[60])/2
def smooth(a):
    out=np.empty_like(a)
    for i in range(366):
        ids=[(i+k)%366 for k in range(-15,16)]
        out[i]=np.mean(a[ids],axis=0)
    return out
thr_s=smooth(thr); clim_s=smooth(clim)
print(np.isnan(thr_s[:,0,0]).sum(), np.isnan(thr_s).sum()/366/ny/nx, np.nanmean(thr_s[:,30,30]), np.nanmean(clim_s[:,30,30]))
