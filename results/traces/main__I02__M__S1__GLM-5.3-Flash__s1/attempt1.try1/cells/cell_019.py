import numpy as np, datetime as dt
tdata=np.load('/tmp/target.npy').astype(np.float64)
tdates=[dt.date(2004,6,1)+dt.timedelta(days=i) for i in range(tdata.shape[0])]
tdoy=np.array([(d-dt.date(d.year,1,1)).days+1 for d in tdates])
thr_sm=np.load('/tmp/thr_sm.npy'); clim_sm=np.load('/tmp/clim_sm.npy')
sea=np.isfinite(tdata).all(axis=0)
thr_t=thr_sm[tdoy-1]
hot=tdata>=thr_t
print("hot days total (sea cells):", hot[sea[None]].sum())
print("hot per day (first 20):", hot.reshape(tdata.shape[0],-1)[:,sea.reshape(-1)].sum(axis=1)[:20])
print("hot per day (max):", hot.reshape(tdata.shape[0],-1)[:,sea.reshape(-1)].sum(axis=1).max())
# sample cell time series vs clim/thr
i,j=40,40
sst=tdata[:,i,j]
print("\ncell(40,40) SST, clim, thr for first 15 days:")
for t in range(15):
    print(tdates[t], f"{sst[t]:.2f} clim={clim_sm[tdoy[t]-1,i,j]:.2f} thr={thr_t[t,i,j]:.2f} hot={hot[t,i,j]}")
diff=(sst-thr_t)
print("\nanomaly sst-thr stats over sea cells:", np.nanmin(diff), np.nanmedian(diff), np.nanmax(diff))
print("fraction hot:", np.nanmean(hot))
# check anomalies vs climatology
diffc=sst[:,None]  # no
anom=tdata - clim_sm[tdoy-1]
print("anom (sst-clim) stats:", np.nanmin(anom), np.nanmedian(anom), np.nanmax(anom))
