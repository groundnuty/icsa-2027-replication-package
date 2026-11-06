from concurrent.futures import ThreadPoolExecutor
def load(d):
    for _ in range(4):
        try:
            with xr.open_dataset(fs.open(f"{p}/sst_{d:%Y%m%d}.nc",'rb'),engine='h5netcdf') as x:
                x=x.sel(latitude=slice(58.685,59.895),longitude=slice(18.685,19.895))
                return x.analysed_sst.values[0].astype('float64'),x.latitude.values,x.longitude.values
        except Exception as e: err=e
    raise err
with ThreadPoolExecutor(16) as ex: r=list(ex.map(load,need))
lat,lon=r[0][1],r[0][2];print(lat[[0,-1]],lon[[0,-1]],r[0][0].shape,r[0][0].dtype)
A=np.stack([a[0] for a in r]);print(A.shape,np.nanmin(A),np.nanmax(A))