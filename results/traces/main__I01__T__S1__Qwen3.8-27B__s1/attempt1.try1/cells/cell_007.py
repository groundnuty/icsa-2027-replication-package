
import fsspec, xarray as xr, numpy as np, time
fs = fsspec.filesystem('onedata')
base = '/icsa2027_data_20261101T090944Z/s1z/'

t0 = time.time()
f = fs.open(base + 'sst_20080601.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
lat = ds['latitude'].values
lon = ds['longitude'].values
print("lat unique check near 54.13/55.33:")
sel = (lat >= 54.12999) & (lat <= 55.33001)
print(lat[sel])
selL = (lon >= 14.66999) & (lon <= 15.87001)
print(lon[selL])
print("n lat in region:", sel.sum(), "n lon in region:", selL.sum())
print("encoding:", ds['analysed_sst'].encoding)
sst = ds['analysed_sst'].isel(latitude=sel, longitude=selL).values
print("sst shape:", sst.shape, "min/max:", np.nanmin(sst), np.nanmax(sst), "nans:", np.isnan(sst).sum())
ds.close()
print("elapsed:", time.time() - t0)
