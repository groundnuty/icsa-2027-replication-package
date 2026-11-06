import xarray as xr, numpy as np, time
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")
enc = ds["analysed_sst"].encoding
print({k: enc.get(k) for k in ("chunksizes","dtype","_FillValue","scale_factor","add_offset")})
print(ds["analysed_sst"].attrs)
lat = ds["latitude"].values; lon = ds["longitude"].values
print("lat range", lat[0], lat[-1], "step", lat[1]-lat[0])
print("lon range", lon[0], lon[-1], "step", lon[1]-lon[0])
# region selection
latmin, latmax, lonmin, lonmax = 63.31, 64.51, 21.31, 22.51
lati = np.where((lat >= latmin) & (lat <= latmax))[0]
loni = np.where((lon >= lonmin) & (lon <= lonmax))[0]
print("n lat cells", len(lati), lat[lati[0]], lat[lati[-1]])
print("n lon cells", len(loni), lon[loni[0]], lon[loni[-1]])
print("lat values:", lat[lati][:5], "...", lat[lati][-3:])
print("lon values:", lon[loni][:5], "...", lon[loni][-3:])
