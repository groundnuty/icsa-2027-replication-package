import xarray as xr
import numpy as np
import os

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

lat = ds['latitude'].values
lon = ds['longitude'].values
t_all = ds['time'].values

lat_min, lat_max, lon_min, lon_max = 54.81, 56.01, 19.61, 20.81
lat_sel = (lat >= lat_min) & (lat <= lat_max)
lon_sel = (lon >= lon_min) & (lon <= lon_max)
print("lats:", lat[lat_sel][0], lat[lat_sel][-1], lat_sel.sum())
print("lons:", lon[lon_sel][0], lon[lon_sel][-1], lon_sel.sum())

# time slices
def tidx(d0, d1):
    a = np.datetime64(d0)
    b = np.datetime64(d1)
    m = (t_all >= a) & (t_all <= b)
    return m

base_mask = tidx("1991-12-27", "2003-01-05")
tgt_mask = tidx("2022-06-01", "2022-08-31")
tb = t_all[base_mask]
tt = t_all[tgt_mask]
print("baseline ext days:", len(tb), tb[0], tb[-1])
print("target days:", len(tt), tt[0], tt[-1])

sst_b = ds['analysed_sst'].isel(time=np.where(base_mask)[0],
                                latitude=np.where(lat_sel)[0],
                                longitude=np.where(lon_sel)[0]).values.astype(np.float64)
sst_t = ds['analysed_sst'].isel(time=np.where(tgt_mask)[0],
                                latitude=np.where(lat_sel)[0],
                                longitude=np.where(lon_sel)[0]).values.astype(np.float64)
ds.close()

print("sst_b shape:", sst_b.shape, "finite frac:", np.isfinite(sst_b).mean())
print("sst_t shape:", sst_t.shape, "finite frac:", np.isfinite(sst_t).mean())
print("target sample values (K):", sst_t[np.isfinite(sst_t)][:5])

os.makedirs("cache", exist_ok=True)
np.savez_compressed("cache/region.npz",
                    sst_base=sst_b, sst_tgt=sst_t,
                    time_base=tb.astype('datetime64[D]').astype(str).encode(),
                    time_tgt=tt.astype('datetime64[D]').astype(str).encode(),
                    lat=lat[lat_sel], lon=lon[lon_sel])
print("cached")