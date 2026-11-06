import shutil, fsspec, numpy as np, h5netcdf, time
st = shutil.disk_usage('/work')
print("/work now: total %.1fG used %.1fG free %.1fG" % (st.total/2**30, st.used/2**30, st.free/2**30))

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
lat0, lat1 = np.searchsorted(lat, 56.63, 'left'), np.searchsorted(lat, 57.83, 'right')
lon0, lon1 = np.searchsorted(lon, 20.23, 'left'), np.searchsorted(lon, 21.43, 'right')
print("lat idx:", lat0, lat1, "n:", lat1-lat0, "lat vals:", lat[lat0], lat[lat1-1])
print("lon idx:", lon0, lon1, "n:", lon1-lon0, "lon vals:", lon[lon0], lon[lon1-1])

# timing for a subset read
t0 = time.time()
sub = np.asarray(v[bi[100], lat0:lat1, lon0:lon1])
print("subset read:", sub.shape, round(time.time()-t0, 3), "s")
