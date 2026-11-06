import numpy as np, datetime as dt
tdata=np.load('/tmp/target.npy').astype(np.float64)
tdoy=np.array([153+i for i in range(tdata.shape[0])])
thr_sm=np.load('/tmp/thr_sm.npy')
sea=np.isfinite(tdata).all(axis=0)
thr_t=thr_sm[tdoy-1]
margin=np.where(sea[None], tdata-thr_t, np.nan)
fin=np.isfinite(margin)
print("closest cell-day to hot/cold boundary (min |margin|):", np.abs(margin[fin]).min())
print("max positive margin (hottest excess):", margin[fin].max())
# how many cell-days within 0.01 K of the boundary?
print("cell-days with |margin|<0.01:", int((np.abs(margin[fin])<0.01).sum()))
