import numpy as np, xarray as xr, os, shutil, time, fsspec
ds = xr.open_dataset('/work/probe/sst_19920101.nc', engine='h5netcdf')
lat = ds.latitude.values; lon = ds.longitude.values
print("lat dtype", lat.dtype, "lon dtype", lon.dtype)
print("lat[0:5]", lat[:5]); print("lat[-3:]", lat[-3:])
print("lon[0:5]", lon[:5]); print("lon[-3:]", lon[-3:])
dlat = np.diff(lat); dlon = np.diff(lon)
print("dlat uniq:", np.unique(np.round(dlat,6))[:5], "dlon uniq:", np.unique(np.round(dlon,6))[:5])
# region selection
latmask = (lat >= 64.51-1e-6) & (lat <= 65.71+1e-6)
lonmask = (lon >= 21.97-1e-6) & (lon <= 23.17+1e-6)
print("n lat cells:", latmask.sum(), "n lon cells:", lonmask.sum())
print("lat sel:", lat[latmask][[0,-1]])
print("lon sel:", lon[lonmask][[0,-1]])
v = ds.analysed_sst
print("units:", v.attrs.get('units'), "| _FillValue:", v.encoding.get('_FillValue'), v.attrs.get('_FillValue'))
print("valid_min/max attrs:", v.attrs.get('valid_min'), v.attrs.get('valid_max'))
sub = v.isel(time=0)[np.ix_(latmask, lonmask)]
print("region sub stats: finite frac", np.isfinite(sub.values).mean(), "min/max", np.nanmin(sub.values), np.nanmax(sub.values))
print("time value:", ds.time.values)
print("disk free GB:", shutil.disk_usage('/work').free/1e9)
# download speed test
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/speedtest', exist_ok=True)
t0=time.time()
for d in ['19920102','19920103','19920104','19920105','19920106','19920107','19920108','19920109','19920110','19920111','19920112','19920113']:
    fs.get(f'{base}/sst_{d}.nc', f'/work/speedtest/sst_{d}.nc')
dt=time.time()-t0
n=len(os.listdir('/work/speedtest'))
print(f"downloaded {n} files in {dt:.2f}s -> {n/dt:.2f} files/s, total MB {sum(os.path.getsize('/work/speedtest/'+f) for f in os.listdir('/work/speedtest'))/1e6:.1f}")
