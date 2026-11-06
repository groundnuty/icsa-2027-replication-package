print('fs' in globals(), 'res' in globals())
def load(d,fs=fs,D=D):
    err=None
    for k in range(4):
        try:
            with fs.open(f"{D}sst_{d:%Y%m%d}.nc",'rb') as f:
                x=xr.open_dataset(f,engine='h5netcdf')
                return x.sel(latitude=slice(58.685,59.895),longitude=slice(18.685,19.895)).load()
        except FileNotFoundError: return None
        except Exception as e: err=e;time.sleep(1)
    return ('err',str(err))
print(load(dates[0]))