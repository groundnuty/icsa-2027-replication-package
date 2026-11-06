import numpy as np, datetime as dt
m=np.load('/work/out/mhw.npy')
f=m.reshape(92,-1).mean(1)
print(np.round(f[::4],2))
th=np.load('/work/thr.npz')['thr']; cl=np.load('/work/thr.npz')['clim']
print(np.nanmean(th[150]), np.nanmean(cl[150]), np.nanmean(th[230]), np.nanmean(cl[230]))
S=np.load('/work/cache/20210715.npy'); print(np.nanmean(S))