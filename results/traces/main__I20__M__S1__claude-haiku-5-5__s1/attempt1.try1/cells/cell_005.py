import pandas as pd, os
from concurrent.futures import ThreadPoolExecutor
def load(dt):
    p=f"{D}/sst_{dt:%Y%m%d}.nc"
    with xr.open_dataset(p,engine="h5netcdf") as d:
        a=d.analysed_sst.isel(time=0).values[np.ix_(li,lj)].astype(np.float64)
        t=pd.Timestamp(d.time.values[0])
    assert t==dt, (t,dt)
    return a
dates=list(pd.date_range("1991-12-27","2003-01-05"))+list(pd.date_range("2012-06-01","2012-08-31"))
with ThreadPoolExecutor(16) as ex: arrs=list(ex.map(load,dates))
A=np.stack(arrs)
np.savez("/tmp/sub.npz",sst=A,dates=np.array([str(d.date()) for d in dates]),lat=lat[li],lon=lon[lj])
print(A.shape, np.isnan(A).mean())