import numpy as np, datetime as dt
tdata=np.load('/tmp/target.npy').astype(np.float64)
tdates=[dt.date(2004,6,1)+dt.timedelta(days=i) for i in range(tdata.shape[0])]
tdoy=np.array([(d-dt.date(d.year,1,1)).days+1 for d in tdates])
thr_sm=np.load('/tmp/thr_sm.npy'); clim_sm=np.load('/tmp/clim_sm.npy')
sea=np.isfinite(tdata).all(axis=0)
thr_t=thr_sm[tdoy-1]
hot=tdata>=thr_t
hot_per_day=hot.reshape(tdata.shape[0],-1)[:,sea.reshape(-1)].sum(axis=1)
print("hot days total (sea cells):", int(hot_per_day.sum()))
print("hot per day (first 20):", hot_per_day[:20])
print("hot per day max:", hot_per_day.max(), "argmax day:", tdates[int(hot_per_day.argmax())])
i,j=40,40
sst=tdata[:,i,j]
print("\ncell(40,40) SST vs clim/thr (first 12 days):")
for t in range(12):
    print(tdates[t], f"SST={sst[t]:.2f} clim={clim_sm[tdoy[t]-1,i,j]:.2f} thr={thr_t[t,i,j]:.2f} hot={bool(hot[t,i,j])}")
print("\nmax SST over sea cells:", np.nanmax(tdata[:,sea]))
print("min thr over sea cells, target days:", np.nanmin(thr_t[:,sea]))
diff=(tdata-thr_t)
print("sst-thr over sea cells: min/median/max:", np.nanmin(diff), np.nanmedian(diff), np.nanmax(diff))
# distribution of where hot occurs spatially
ys,xs=np.where(hot.any(axis=0))
print("cells with any hot day:", len(ys))
