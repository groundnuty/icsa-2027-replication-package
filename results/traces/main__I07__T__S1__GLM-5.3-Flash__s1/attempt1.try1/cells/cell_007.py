import fsspec, xarray as xr, numpy as np, time
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
# check boundary/extension files exist
for p in ['sst_19911226.nc','sst_19911227.nc','sst_19911231.nc','sst_20030101.nc','sst_20030105.nc','sst_20030106.nc','sst_19920101.nc','sst_20021231.nc']:
    try:
        fs.info(f"{base}/{p}"); print("EXISTS", p)
    except Exception as ex:
        print("MISSING", p)
# region index selection from reference file
f = fs.open(f"{base}/sst_19920101.nc","rb")
ds = xr.open_dataset(f, engine="h5netcdf")
lat = ds.latitude.values; lon = ds.longitude.values
lat_b = (lat >= np.float32(54.45-1e-6)) & (lat <= np.float32(55.65+1e-6))
lon_b = (lon >= np.float32(16.05-1e-6)) & (lon <= np.float32(17.25+1e-6))
ila, ila2 = np.where(lat_b)[0][[0,-1]]; ilo, ilo2 = np.where(lon_b)[0][[0,-1]]
print("lat idx", ila, ila2, "n=", ila2-ila+1, "vals", lat[ila], lat[ila2])
print("lon idx", ilo, ilo2, "n=", ilo2-ilo+1, "vals", lon[ilo], lon[ilo2])
t0=time.time()
sub = ds.analysed_sst.isel(time=0, latitude=slice(ila,ila2+1), longitude=slice(ilo,ilo2+1)).values
print("read region:", time.time()-t0, "s shape", sub.shape, "finite frac:", np.isfinite(sub).mean())
