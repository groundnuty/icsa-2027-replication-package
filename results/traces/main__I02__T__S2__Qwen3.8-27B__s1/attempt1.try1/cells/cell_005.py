import fsspec, xarray as xr, numpy as np, os, time as _t
os.makedirs('output', exist_ok=True)
os.makedirs('work', exist_ok=True)
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
lat = ds.latitude.values; lon = ds.longitude.values; t = ds.time.values
eps = 1e-6
li = np.where((lat >= 54.17-eps) & (lat <= 55.37+eps))[0]
lo = np.where((lon >= 13.25-eps) & (lon <= 14.45+eps))[0]
def idx(ts): return int(np.searchsorted(t, np.datetime64(ts)))
i0, i1 = idx('1991-12-27'), idx('2003-01-05')
j0, j1 = idx('2004-06-01'), idx('2004-08-31')
print("region rows", len(li), "cols", len(lo))
print("ext baseline:", i0, i1, i1-i0+1, "| target:", j0, j1, j1-j0+1)
t0=_t.time()
SB = ds['analysed_sst'].isel(time=slice(i0,i1+1), latitude=slice(int(li[0]),int(li[-1])+1), longitude=slice(int(lo[0]),int(lo[-1])+1)).values.astype(np.float64)
ST = ds['analysed_sst'].isel(time=slice(j0,j1+1), latitude=slice(int(li[0]),int(li[-1])+1), longitude=slice(int(lo[0]),int(lo[-1])+1)).values.astype(np.float64)
print(f"load: {_t.time()-t0:.1f}s, SB{SB.shape} ST{ST.shape}")
print("SB finite frac:", np.isfinite(SB).mean(), "ST finite frac:", np.isfinite(ST).mean())
np.savez_compressed('work/sst.npz', SB=SB, ST=ST, lat=lat[li].astype(np.float32), lon=lon[lo].astype(np.float32),
                    tb=t[i0:i1+1].astype('datetime64[ns]'), tt=t[j0:j1+1].astype('datetime64[ns]'))
print("npz size MB:", os.path.getsize('work/sst.npz')/1e6)
