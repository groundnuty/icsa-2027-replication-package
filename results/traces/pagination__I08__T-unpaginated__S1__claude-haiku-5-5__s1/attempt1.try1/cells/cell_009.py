thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):  # a: (367,ncell), index 1..366
    out=np.full_like(a,np.nan)
    v=a[1:367]  # 366 x ncell
    for i in range(366):
        idx=[(i+k)%366 for k in range(-15,16)]
        out[i+1]=np.mean(v[idx],axis=0)
    return out
thr_s=smooth(thr); clim_s=smooth(clim)
# target
tmask=(alld>=pd.Timestamp('2007-06-01'))&(alld<=pd.Timestamp('2007-08-31'))
tidx=np.where(tmask)[0]; tday=alld[tidx]
T=arr[tidx]  # (92, 60,60)
sea=np.all(np.isfinite(T),axis=0).reshape(-1)
print('sea cells', sea.sum(), 'of', ncell)
Tf=T.reshape(len(tidx),-1)
tdoy=doys[tidx]
thr_t=thr_s[tdoy]  # (92,ncell)
with np.errstate(invalid='ignore'):
    hot=(Tf>=thr_t)&np.isfinite(thr_t)
hot &= sea[None,:]
def cell_mhw(h):
    n=len(h); m=np.zeros(n,bool)
    # candidate runs >=5
    runs=[]; i=0
    while i<n:
        if h[i]:
            j=i
            while j<n and h[j]: j+=1
            if j-i>=5: runs.append([i,j-1])
            i=j
        else: i+=1
    # join gaps of 1-2 non-hot days
    merged=[]
    for r in runs:
        if merged and (r[0]-merged[-1][1]-1) in (1,2):
            merged[-1][1]=r[1]
        else: merged.append(list(r))
    for a,b in merged: m[a:b+1]=True
    return m
M=np.zeros_like(hot)
for c in np.where(sea)[0]:
    M[:,c]=cell_mhw(hot[:,c])
active=M.any(axis=1)
events=[]; i=0; n=len(active)
while i<n:
    if active[i]:
        j=i
        while j<n and active[j]: j+=1
        events.append((tday[i].strftime('%Y-%m-%d'), tday[j-1].strftime('%Y-%m-%d'))); i=j
    else: i+=1
print(events); print('active days', active.sum(), 'cells ever', M.any(0).sum())
