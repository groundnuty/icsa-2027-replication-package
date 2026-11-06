import numpy as np
z=np.load('/work/a.npz');T=z['T'];B=z['B']
sea=np.isfinite(T).all(0)
print(np.isfinite(B[:,sea]).mean(), np.isfinite(B).mean(), np.nanmin(T),np.nanmax(T))
print(np.isfinite(B[:,sea]).mean(1)[::300])
x=np.nanmean(B[:,sea],1)
print(np.nanmean(T[:,sea],1)[::10])