import warnings; warnings.filterwarnings('ignore')
nE=4028
Sx=S[:nE]; Dx=D[:nE]; Bx=base_mask[:nE]
thr=np.full((367,60,60),np.nan); clim=np.full((367,60,60),np.nan)
for dd in range(1,367):
    if dd==60: continue
    c=(Bx&(Dx==dd)).astype(float)
    if c.sum()==0: continue
    pm=convolve1d(c,np.ones(11),mode='constant',cval=0)>0
    pool=Sx[pm]
    thr[dd]=np.nanpercentile(pool,90,axis=0,method='hazen')
    clim[dd]=np.nanmean(pool,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    # a: (367,...) with index 0 unused; use 1..366 array
    arr=a[1:]  # 366 elements
    out=np.zeros_like(arr)
    for k in range(-15,16):
        out+=np.roll(arr,-k,axis=0)
    return out/31.0
thrS=np.full((367,60,60),np.nan); climS=np.full((367,60,60),np.nan)
thrS[1:]=smooth(thr); climS[1:]=smooth(clim)
print(np.isnan(thrS[1:]).sum(), np.isnan(climS[1:]).sum(), np.isnan(thr[1:]).sum())
# sea cells
tgt=S[nE:]; print(tgt.shape)
sea=np.all(np.isfinite(tgt),axis=0); print('sea cells', sea.sum())
print('sea cells with nan thr', (sea & np.isnan(thrS[1:]).any(axis=0)).sum())