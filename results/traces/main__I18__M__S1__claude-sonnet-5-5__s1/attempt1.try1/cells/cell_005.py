from concurrent.futures import ThreadPoolExecutor
def load(x):
    with xr.open_dataset(f"{d}/sst_{x:%Y%m%d}.nc",engine='h5netcdf') as a:
        a=a.analysed_sst.sel(latitude=slice(57.12,58.34),longitude=slice(22.78,24.0))
        return a.isel(time=0).values.astype('float64'),a.latitude.values,a.longitude.values
with ThreadPoolExecutor(16) as ex: R=list(ex.map(load,dates))
lat,lon=R[0][1],R[0][2];print(lat[[0,-1]],lon[[0,-1]],len(lat),len(lon))
A=np.stack([r[0] for r in R]);print(A.shape,np.nanmin(A),np.nanmax(A))
tx=pd.date_range('2010-06-01','2010-08-31');T=np.stack([load(x)[0] for x in tx])