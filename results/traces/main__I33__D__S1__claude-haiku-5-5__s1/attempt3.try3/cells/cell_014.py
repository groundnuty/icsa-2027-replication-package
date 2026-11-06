import os, glob, numpy as np, xarray as xr, datetime
fl=sorted(glob.glob('/work/sst/sst_*.nc'))
ds0=xr.open_dataset(fl[0],engine='h5netcdf')
lat=ds0.latitude.values; lon=ds0.longitude.values
li=np.where((lat>=59.05-1e-6)&(lat<=60.25+1e-6))[0]; lo=np.where((lon>=21.25-1e-6)&(lon<=22.45+1e-6))[0]
dates=[]; arrs=[]
for f in fl:
    with xr.open_dataset(f,engine='h5netcdf') as d:
        t=d.time.values
        assert t.size==1
        dates.append(np.datetime64(t[0],'D'))
        arrs.append(d.analysed_sst.isel(latitude=li,longitude=lo).values[0].astype(np.float64))
        assert np.allclose(d.latitude.values[li], lat[li]) and np.allclose(d.longitude.values[lo], lon[lo])
dates=np.array(dates); arr=np.stack(arrs)
o=np.argsort(dates); dates=dates[o]; arr=arr[o]
print(arr.shape, dates[0], dates[-1], len(np.unique(dates)))
print('nan frac', np.isnan(arr).mean(), 'min', np.nanmin(arr), 'max', np.nanmax(arr))
np.savez('/work/region.npz', dates=dates.astype('datetime64[D]').astype(str), sst=arr, lat=lat[li], lon=lon[lo])