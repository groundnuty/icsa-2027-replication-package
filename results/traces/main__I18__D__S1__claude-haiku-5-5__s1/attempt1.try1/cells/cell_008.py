import datetime as dt
from concurrent.futures import ThreadPoolExecutor
os.makedirs('/work/cache', exist_ok=True)
days=[]
d=dt.date(1991,12,27)
while d<=dt.date(2003,1,5):
    days.append(d); d+=dt.timedelta(1)
d=dt.date(2010,6,1)
while d<=dt.date(2010,8,31):
    days.append(d); d+=dt.timedelta(1)
print(len(days))
def proc(d):
    s=d.strftime('%Y%m%d'); out=f'/work/cache/{s}.npz'
    if os.path.exists(out): return s, 'cached'
    loc=f'/work/d/raw_{s}.nc'
    fs.get(base+f'sst_{s}.nc', loc)
    x=xr.open_dataset(loc, engine='h5netcdf')
    v=x.analysed_sst.isel(time=0, latitude=slice(182,242), longitude=slice(690,750)).values.astype(np.float64)
    tt=x.time.values[0]
    la_=x.latitude.values[182:242]; lo_=x.longitude.values[690:750]
    x.close(); os.remove(loc)
    np.savez(out, sst=v, lat=la_, lon=lo_, time=str(tt)[:10])
    return s,'ok'
t=time.time()
with ThreadPoolExecutor(8) as ex:
    res=list(ex.map(lambda d: proc(d), days[:50]))
print(time.time()-t, res[:3])