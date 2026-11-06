import pandas as pd,numpy as np,time
from concurrent.futures import ThreadPoolExecutor
dates=list(pd.date_range('1991-12-27','2003-01-05'))+list(pd.date_range('2013-06-01','2013-08-31'))
def get(dt):
    n=f"sst_{dt:%Y%m%d}.nc"; lp='/work/'+n
    for k in range(4):
        try:
            if not os.path.exists(lp): fs.get(p+'/'+n,lp)
            d=xr.open_dataset(lp,engine='h5netcdf')
            d=d.sel(latitude=slice(57.405,58.615),longitude=slice(18.685,19.895)).load()
            r=(d.analysed_sst.values[0].astype('float64'),d.latitude.values,d.longitude.values,d.analysed_sst.attrs)
            d.close(); os.remove(lp); return r
        except Exception as e: err=e; time.sleep(1)
    return ('ERR',str(err))
t=time.time()
with ThreadPoolExecutor(16) as ex: res=list(ex.map(get,dates[:32]))
print(time.time()-t,[r[0] for r in res if isinstance(r[0],str)][:3]); print(res[0][0].shape,res[0][1][[0,-1]],res[0][2][[0,-1]],res[0][3])