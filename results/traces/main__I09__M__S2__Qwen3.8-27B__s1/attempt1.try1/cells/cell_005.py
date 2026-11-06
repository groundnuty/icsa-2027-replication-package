import numpy as np, os, xarray as xr
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")
t_all = ds['time'].values
lat = ds['latitude'].values
lon = ds['longitude'].values
lat_min, lat_max, lon_min, lon_max = 54.81, 56.01, 19.61, 20.81
lat_sel = (lat >= lat_min) & (lat <= lat_max)
lon_sel = (lon >= lon_min) & (lon <= lon_max)
base_mask = (t_all >= np.datetime64("1991-12-27")) & (t_all <= np.datetime64("2003-01-05"))
tgt_mask = (t_all >= np.datetime64("2022-06-01")) & (t_all <= np.datetime64("2022-08-31"))
sst_b = ds['analysed_sst'].isel(time=np.where(base_mask)[0],
                                latitude=np.where(lat_sel)[0],
                                longitude=np.where(lon_sel)[0]).values.astype(np.float64)
sst_t = ds['analysed_sst'].isel(time=np.where(tgt_mask)[0],
                                latitude=np.where(lat_sel)[0],
                                longitude=np.where(lon_sel)[0]).values.astype(np.float64)
tb = t_all[base_mask].astype('datetime64[D]')
tt = t_all[tgt_mask].astype('datetime64[D]')
ds.close()
os.makedirs("cache", exist_ok=True)
np.savez_compressed("cache/region.npz",
                    sst_base=sst_b, sst_tgt=sst_t,
                    time_base=tb.astype(str), time_tgt=tt.astype(str),
                    lat=lat[lat_sel], lon=lon[lon_sel])
d = np.load("cache/region.npz")
print({k: (v.shape, v.dtype) for k, v in d.items()})