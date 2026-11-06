import os, time, numpy as np, xarray as xr, pandas as pd
from concurrent.futures import ThreadPoolExecutor
D="/data/icsa2027_data_20261101T090944Z/s1z"
dates=pd.date_range("1991-12-27","2003-01-05").tolist()+pd.date_range("2020-06-01","2020-08-31").tolist()
li0,li1,lo0,lo1=45,105,463,523
def load(d):
    p=f"{D}/sst_{d:%Y%m%d}.nc"
    with xr.open_dataset(p,engine="h5netcdf") as x:
        t=pd.Timestamp(x.time.values[0])
        assert t==pd.Timestamp(d), (t,d)
        return x.analysed_sst.values[0,li0:li1,lo0:lo1].astype(np.float64)
t0=time.time()
with ThreadPoolExecutor(8) as ex: arrs=list(ex.map(load,dates))
A=np.stack(arrs); print(A.shape, time.time()-t0)
np.savez("/tmp/sst_sub.npz", A=A, dates=np.array([str(d.date()) for d in dates]))