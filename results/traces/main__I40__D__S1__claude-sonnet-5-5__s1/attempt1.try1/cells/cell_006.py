import numpy as np
from concurrent.futures import ThreadPoolExecutor
dates=list(pd.date_range('1991-12-27','2003-01-05'))+list(pd.date_range('2009-06-01','2009-08-31'))
def get(d):
    s=d.strftime('%Y%m%d'); p=f'/work/d/{s}.nc'
    for t in range(4):
        try:
            fs.get(R+f'/sst_{s}.nc',p)
            x=xr.open_dataset(p,engine='h5netcdf')
            la=x.latitude.values; lo=x.longitude.values
            m=(la>=61.57-1e-4)&(la<=62.77+1e-4); n=(lo>=20.17-1e-4)&(lo<=21.37+1e-4)
            v=x.analysed_sst.values[0][np.ix_(m,n)].astype('float64') if False else x.analysed_sst.values[0][np.ix_(m,n)]
            r=(v,la[m],lo[n],x.analysed_sst.dtype); x.close(); os.remove(p); return r
        except Exception as e: err=e
    return ('err',str(err))
with ThreadPoolExecutor(16) as ex: res=list(ex.map(get,dates))
print(sum(r[0]=='err' for r in res), res[0][1:3] if res[0][0]!='err' else res[0])