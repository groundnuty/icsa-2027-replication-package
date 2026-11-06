
b0,b1=pd.Timestamp('1991-12-27'),pd.Timestamp('2003-01-05')
base=sub.analysed_sst.sel(time=slice(b0,b1)).load().values.astype(np.float64)
btime=pd.DatetimeIndex(sub.time.sel(time=slice(b0,b1)).values)
tgt=sub.analysed_sst.sel(time=slice('2021-06-01','2021-08-31')).load().values.astype(np.float64)
ttime=pd.DatetimeIndex(sub.time.sel(time=slice('2021-06-01','2021-08-31')).values)
print(base.shape,tgt.shape, btime[0],btime[-1], ttime[0],ttime[-1])
# doy mapping (leap-style numbering)
cum=[0,31,60,91,121,152,182,213,244,274,305,335]  # days before month, leap-style (Feb has 29)
def doy(t):
    return cum[t.month-1]+t.day
bd=pd.DatetimeIndex([t for t in btime if pd.Timestamp('1992-01-01')<=t<=pd.Timestamp('2002-12-31')])
print(len(bd), doy(pd.Timestamp('2021-03-01')))
# index of baseline dates
idx={t:i for i,t in enumerate(btime)}
ny,nx=base.shape[1:]
thr=np.full((367,ny,nx),np.nan); clim=np.full((367,ny,nx),np.nan)
for d in range(1,367):
    if d==60: continue
    dates=set()
    for b in bd:
        if doy(b)==d:
            for k in range(-5,6): dates.add(b+pd.Timedelta(days=k))
    dates=sorted(t for t in dates if t in idx)
    pool=base[[idx[t] for t in dates]]
    thr[d]=np.nanquantile(pool,0.9,axis=0,method='hazen')
    clim[d]=np.nanmean(pool,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
thr=thr[1:367]; clim=clim[1:367]
def smooth(a):
    out=np.empty_like(a)
    for d in range(366):
        ii=[(d+k)%366 for k in range(-15,16)]
        out[d]=a[ii].mean(axis=0)
    return out
thrS=smooth(thr); climS=smooth(clim)
print(np.isnan(thrS).sum(axis=(1,2))[[0,100,200]], np.isnan(thrS[:, 0,0]).sum())
