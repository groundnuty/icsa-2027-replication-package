import fsspec, xarray as xr, numpy as np, time
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

def read_region(dstr):
    f = fs.open(base + f'/sst_{dstr}.nc', "rb")
    ds = xr.open_dataset(f, engine="h5netcdf")
    lat = ds.latitude.values; lon = ds.longitude.values
    latm = (lat >= 57.83-1e-9) & (lat <= 59.03+1e-9)
    lonm = (lon >= 17.41-1e-9) & (lon <= 18.61+1e-9)
    v = ds['analysed_sst'].isel(latitude=np.where(latm)[0], longitude=np.where(lonm)[0]).values[0]
    f.close()
    return v.astype(np.float64)

for d in ['19920715','19960229','20030105','20070831']:
    t0=time.time()
    v = read_region(d)
    print(d, "read+close:", round(time.time()-t0,2), "s; finite:", np.isfinite(v).sum(), "min/max:", np.nanmin(v).round(2), np.nanmax(v).round(2))
