import time
from concurrent.futures import ThreadPoolExecutor
def load(r):
    p=f"{d}/sst_{r:%Y%m%d}.nc"
    with xr.open_dataset(p,engine='h5netcdf') as x:
        v=x.analysed_sst.values[0,ii[0]:ii[-1]+1,jj[0]:jj[-1]+1].astype(np.float64)
        return v
t0=time.time()
with ThreadPoolExecutor(16) as ex: arrs=list(ex.map(load, req))
print(time.time()-t0)
S=np.stack(arrs); print(S.shape, np.isnan(S).mean())
np.save('/tmp/S.npy',S)