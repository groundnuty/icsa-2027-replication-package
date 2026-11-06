import fsspec, xarray as xr, numpy as np, io, time
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
dates = ['1992%02d%02d'%(6,d) for d in range(1,11)]
t0=time.time()
data = fs.cat([f'{base}/sst_{d}.nc' for d in dates])
t1=time.time()
outs=[]
for d in dates:
    b = io.BytesIO(data[f'{base}/sst_{d}.nc'])
    with xr.open_dataset(b, engine='h5netcdf') as ds:
        v = ds['analysed_sst'].isel(time=0).values  # full field
        outs.append(v.astype('float64'))
t2=time.time()
print('cat:', t1-t0, 'decode all:', t2-t1, 'total:', t2-t0)
print(outs[0].shape, outs[0].dtype, np.nanmean(outs[0]))
