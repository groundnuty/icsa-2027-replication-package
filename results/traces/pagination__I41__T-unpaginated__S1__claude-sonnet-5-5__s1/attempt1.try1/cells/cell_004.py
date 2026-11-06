from concurrent.futures import ThreadPoolExecutor
def load(d):
    for t in range(4):
        try:
            with xr.open_dataset(fs.open(f"{p}/sst_{d:%Y%m%d}.nc",'rb'),engine='h5netcdf',decode_times=False) as x:
                v=x.analysed_sst
                la=x.latitude.values.astype('float64'); lo=x.longitude.values.astype('float64')
                return v.values[0],la,lo
        except Exception as e: err=e
    raise err
r=load(need[0]);print(r[0].shape,np.nanmean(r[0]))
la,lo=r[1],r[2]
print(la[:3],la.dtype)