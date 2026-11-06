import pandas as pd,numpy as np,time,threading
from concurrent.futures import ThreadPoolExecutor
lock=threading.Lock()
dates=list(pd.date_range('1991-12-27','2003-01-05'))+list(pd.date_range('2013-06-01','2013-08-31'))
def get(dt):
    n=f"sst_{dt:%Y%m%d}.nc"; lp='/work/'+n; err=None
    for k in range(4):
        try:
            fs.get(p+'/'+n,lp)
            with lock:
                d=xr.open_dataset(lp,engine='h5netcdf')
                d=d.sel(latitude=slice(57.405,58.615),longitude=slice(18.685,19.895)).load(); d.close()
            os.remove(lp)
            return d.analysed_sst.values[0].astype('float64'),d.latitude.values,d.longitude.values
        except Exception as e: err=repr(e); time.sleep(1)
    return err
t=time.time()
with ThreadPoolExecutor(16) as ex: res=list(ex.map(get,dates[:32]))
print(time.time()-t,[r for r in res if isinstance(r,str)][:2])