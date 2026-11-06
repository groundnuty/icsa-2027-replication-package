import numpy as np, xarray as xr, os, shutil, time, fsspec
ds = xr.open_dataset('/work/probe/sst_19920101.nc', engine='h5netcdf')
lat = ds.latitude.values; lon = ds.longitude.values
latmask = (lat >= 64.51-1e-6) & (lat <= 65.71+1e-6)
lonmask = (lon >= 21.97-1e-6) & (lon <= 23.17+1e-6)
sub = ds.analysed_sst.values[0][np.ix_(latmask, lonmask)]
print("region shape:", sub.shape)
print("finite frac:", np.isfinite(sub).mean(), "min/max:", np.nanmin(sub), np.nanmax(sub))
# how many cells finite on this winter day?
print("n finite cells:", np.isfinite(sub).sum(), "of", sub.size)
# NaN pattern: check a summer file too
print("disk free GB:", shutil.disk_usage('/work').free/1e9)
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/speedtest', exist_ok=True)
t0=time.time()
for d in ['19920102','19920103','19920104','19920105','19920106','19920107','19920108','19920109','19920110','19920111','19920112','19920113']:
    fs.get(f'{base}/sst_{d}.nc', f'/work/speedtest/sst_{d}.nc')
dt=time.time()-t0
n=len(os.listdir('/work/speedtest'))
mb=sum(os.path.getsize('/work/speedtest/'+f) for f in os.listdir('/work/speedtest'))/1e6
print(f"downloaded {n} files in {dt:.2f}s -> {n/dt:.2f} files/s, total {mb:.1f} MB")
