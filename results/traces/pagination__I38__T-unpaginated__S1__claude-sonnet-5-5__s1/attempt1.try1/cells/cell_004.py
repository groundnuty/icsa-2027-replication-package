import numpy as np, pandas as pd, time
from concurrent.futures import ThreadPoolExecutor
dates=pd.date_range('1991-12-27','2003-08-31')
avail={n.split('_')[-1][:8] for n in names}
miss=[d for d in dates if d.strftime('%Y%m%d') not in avail];print(len(dates),len(miss),miss[:5])
def load(d):
    for t in range(4):
        try:
            with fs.open(f"{p}/sst_{d.strftime('%Y%m%d')}.nc",'rb') as f:
                x=xr.open_dataset(f,engine='h5netcdf')
                x=x.sel(latitude=slice(60.485,61.695),longitude=slice(17.245,18.455)).load()
            return x.analysed_sst.values[0],x.latitude.values,x.longitude.values
        except Exception as e: err=e
    raise err
t=time.time();r=load(dates[0]);print(r[0].shape,time.time()-t,r[1],r[2])