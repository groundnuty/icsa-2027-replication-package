import fsspec, numpy as np, h5netcdf, time

fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
nc = h5netcdf.File(f, 'r')
v = nc['analysed_sst']
traw = np.asarray(nc['time'][:])
t64 = np.datetime64('1981-01-01T00:00:00') + traw.astype('timedelta64[s]')
ti = np.where((t64 >= np.datetime64('2010-06-01')) & (t64 <= np.datetime64('2010-08-31')))[0]
bi = np.where((t64 >= np.datetime64('1991-12-27')) & (t64 <= np.datetime64('2003-01-05')))[0]

lat = np.asarray(nc['latitude'][:]).astype('float64')
lon = np.asarray(nc['longitude'][:]).astype('float64')
lat0, lat1 = 157, 217   # from searchsorted
lon0, lon1 = 562, 622

# collect subset into in-RAM arrays (target 92x60x60 f32 = 1.3MB; baseline 4028x60x60 f32 = 55MB)
t0 = time.time()
target = np.stack([np.asarray(v[i, lat0:lat1, lon0:lon1], dtype=np.float32) for i in ti])
print("target subset:", target.shape, target.dtype, round(time.time()-t0,1), "s")
t0 = time.time()
base = np.empty((len(bi), 60, 60), dtype=np.float32)
for k, i in enumerate(bi):
    base[k] = np.asarray(v[i, lat0:lat1, lon0:lon1], dtype=np.float32)
print("baseline subset:", base.shape, round(time.time()-t0,1), "s")

np.save('/work/me/target.npy', target)
np.save('/work/me/base.npy', base)
np.save('/work/me/times_target.npy', t64[ti])
np.save('/work/me/times_base.npy', t64[bi])
np.save('/work/me/latlon_idx.npy', np.array([lat0, lat1, lon0, lon1]))
np.save('/work/me/lat_sub.npy', lat[lat0:lat1])
np.save('/work/me/lon_sub.npy', lon[lon0:lon1])
print("saved.")
