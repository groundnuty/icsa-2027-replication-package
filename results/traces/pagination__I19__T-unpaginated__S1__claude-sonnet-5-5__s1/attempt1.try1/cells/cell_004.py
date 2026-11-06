from concurrent.futures import ThreadPoolExecutor
import time
def load(x):
    for k in range(4):
        try:
            with xr.open_dataset(fs.open(f'{p}/sst_{x:%Y%m%d}.nc','rb'),engine='h5netcdf') as a:
                a=a.sel(latitude=slice(57.12,58.34),longitude=slice(22.78,24.0))
                return a.analysed_sst.values[0].astype('float64'),a.latitude.values,a.longitude.values
        except Exception as e: err=e
    raise err
t0=time.time()
alld=list(d)+list(t)
with ThreadPoolExecutor(16) as ex: res=list(ex.map(load,alld:=alld if False else alld)) if False else list(ex.map(load,alld))
print(time.time()-t0)
lat,lon=res[0][1],res[0][2];print(lat,lon,res[0][0].shape)
arr=np.stack([r[0] for r in res]);np.save('/tmp/a.npy',arr)