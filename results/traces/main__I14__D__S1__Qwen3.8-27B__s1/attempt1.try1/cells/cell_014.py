import xarray as xr, numpy as np
ds = xr.open_dataset('/work/data/sst_s2.nc', engine="h5netcdf")
lat = ds['latitude'].values  # float32
lon = ds['longitude'].values
latm = (lat >= np.float64(56.13)) & (lat <= np.float64(57.33))
lonm = (lon >= np.float64(17.71)) & (lon <= np.float64(18.91))
lati = np.flatnonzero(latm); loni = np.flatnonzero(lonm)
print("n lat:", len(lati), lat[lati][0], "->", lat[lati][-1])
print("n lon:", len(loni), lon[loni][0], "->", lon[loni][-1])
print("lat contiguous:", lati[0]+len(lati)-1 == lati[-1], "lon contiguous:", loni[0]+len(loni)-1 == loni[-1])

tv = ds['time'].values
def tidx(d):
    i = int(np.searchsorted(tv, np.datetime64(d)))
    assert tv[i] == np.datetime64(d), d
    return i
i_b0 = tidx('1991-12-27'); i_b1 = tidx('2003-01-05')
i_t0 = tidx('2015-06-01'); i_t1 = tidx('2015-08-31')
print("baseline idx", i_b0, i_b1, "len", i_b1-i_b0+1)
print("target idx", i_t0, i_t1, "len", i_t1-i_t0+1)

v = ds['analysed_sst']
B = v.isel(time=slice(i_b0, i_b1+1), latitude=lati, longitude=loni).values  # (4028, nl, no) f32
T = v.isel(time=slice(i_t0, i_t1+1), latitude=lati, longitude=loni).values  # (92, nl, no) f32
print("B", B.shape, B.dtype, "T", T.shape, T.dtype)
B = B.astype(np.float64); T = T.astype(np.float64)
np.save('/work/data/B.npy', B)
np.save('/work/data/T.npy', T)
np.save('/work/data/lat_sel.npy', ds['latitude'].values[lati])
np.save('/work/data/lon_sel.npy', ds['longitude'].values[loni])
# save time arrays too
np.save('/work/data/tb.npy', tv[i_b0:i_b1+1])
np.save('/work/data/tt.npy', tv[i_t0:i_t1+1])
print("saved. finite frac target:", np.isfinite(T).mean(), "baseline:", np.isfinite(B).mean())