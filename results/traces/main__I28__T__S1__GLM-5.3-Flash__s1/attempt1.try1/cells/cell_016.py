import fsspec, xarray as xr, numpy as np, time
from datetime import date, timedelta
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
latmin, latmax, lonmin, lonmax = 57.85, 59.05, 21.01, 22.21

def daterange(a,b):
    out=[]; d=a
    while d<=b:
        out.append(d); d+=timedelta(days=1)
    return out

dates = daterange(date(1991,12,27), date(2003,1,5)) + daterange(date(2013,6,1), date(2013,8,31))

# grid indices (from earlier probe, recompute here for safety)
with fs.open(f'{base}/sst_20130601.nc','rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    lat = ds.latitude.values.astype('float64'); lon = ds.longitude.values.astype('float64')
    ds.close()
li = np.where((lat>=latmin-1e-9)&(lat<=latmax+1e-9))[0]
oi = np.where((lon>=lonmin-1e-9)&(lon<=lonmax+1e-9))[0]
np.save('/tmp/li.npy', li); np.save('/tmp/oi.npy', oi)
np.save('/tmp/latvals.npy', lat[li]); np.save('/tmp/lonvals.npy', lon[oi])
with fs.open(f'{base}/sst_20130601.nc','rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    tim = ds.time.values
    ds.close()
np.save('/tmp/tvals.npy', tim)

data = np.full((len(dates), 60, 60), np.nan, dtype='float64')
t0=time.time(); ndone=0
for i,d in enumerate(dates):
    nm = f'sst_{d:%Y%m%d}.nc'
    with fs.open(f'{base}/{nm}','rb') as f:
        ds = xr.open_dataset(f, engine='h5netcdf')
        v = ds.analysed_sst.isel(time=0, latitude=li, longitude=oi).values.astype('float64')
        ds.close()
    data[i] = v
    ndone+=1
    if ndone % 100 == 0:
        print(f"{ndone} files, {time.time()-t0:.0f}s elapsed, rate {ndone/(time.time()-t0):.2f}/s", flush=True)
np.save('/tmp/chunk1.npy', data)
print("chunk1 done:", data.shape, "time %.0fs" % (time.time()-t0))
