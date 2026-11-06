import numpy as np, pandas as pd
from concurrent.futures import ThreadPoolExecutor
R='/data/icsa2027_data_20261101T090944Z/s1z/sst_%s.nc'
lat=d.latitude.values;lon=d.longitude.values
li=np.where((lat>=54.17-1e-4)&(lat<=55.37+1e-4))[0];lo=np.where((lon>=13.25-1e-4)&(lon<=14.45+1e-4))[0]
print(lat[li][[0,-1]],lon[lo][[0,-1]],len(li),len(lo))
def ld(t):
    f=R%t.strftime('%Y%m%d')
    if not os.path.exists(f): return None
    with xr.open_dataset(f,engine='h5netcdf') as x:
        return x.analysed_sst.values[0,li[0]:li[-1]+1,lo[0]:lo[-1]+1].astype('float64')
bd=pd.date_range('1991-12-27','2003-01-05');td=pd.date_range('2004-06-01','2004-08-31')
with ThreadPoolExecutor(16) as ex:
    B=list(ex.map(ld,bd));T=list(ex.map(ld,td))
print(sum(b is None for b in B),sum(b is None for b in T))