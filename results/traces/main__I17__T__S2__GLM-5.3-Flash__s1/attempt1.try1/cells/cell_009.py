import fsspec, numpy as np, h5netcdf, time, os

fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
nc = h5netcdf.File(f, 'r')
v = nc['analysed_sst']

traw = np.asarray(nc['time'][:])
t64 = np.datetime64('1981-01-01T00:00:00') + traw.astype('timedelta64[s]')
print("time range:", t64[0], t64[-1], "n:", len(t64))
# check continuity
print("unique diffs (days):", np.unique(np.diff(t64).astype('timedelta64[D]')))

t_start, t_end = np.datetime64('2010-06-01'), np.datetime64('2010-08-31')
b_start, b_end = np.datetime64('1991-12-27'), np.datetime64('2003-01-05')

tmask = (t64 >= t_start) & (t64 <= t_end)
bmask = (t64 >= b_start) & (t64 <= b_end)
ti = np.where(tmask)[0]
bi = np.where(bmask)[0]
print("target days:", len(ti), t64[ti[0]], t64[ti[-1]])
print("baseline read days:", len(bi), t64[bi[0]], t64[bi[-1]])

os.makedirs('~/me', exist_ok=True)
Ta = len(ti); Tb = len(bi)
tgt = np.lib.format.open_memmap('~/me/sst_target.npy', mode='w+', dtype=np.float32, shape=(Ta, 626, 1051))
bas = np.lib.format.open_memmap('~/me/sst_base.npy', mode='w+', dtype=np.float32, shape=(Tb, 626, 1051))

t0 = time.time()
for k, idx in enumerate(ti):
    tgt[k] = np.asarray(v[idx, :, :])
print("target done in", round(time.time()-t0, 1), "s")

t0 = time.time()
for k, idx in enumerate(bi):
    bas[k] = np.asarray(v[idx, :, :])
print("baseline done in", round(time.time()-t0, 1), "s")

tgt.flush(); bas.flush()
np.save('~/me/times_target.npy', t64[ti])
np.save('~/me/times_base.npy', t64[bi])
np.save('~/me/lat.npy', np.asarray(nc['latitude'][:]))
np.save('~/me/lon.npy', np.asarray(nc['longitude'][:]))
print("saved.")
