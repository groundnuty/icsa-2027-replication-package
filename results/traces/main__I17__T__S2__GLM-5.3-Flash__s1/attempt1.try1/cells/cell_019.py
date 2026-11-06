import numpy as np, fsspec, h5netcdf

me = '/work/me/'
target = np.load(me+'target.npy')
tt = np.load(me+'times_target.npy')
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','rb')
nc = h5netcdf.File(f,'r'); v = nc['analysed_sst']
traw = np.asarray(nc['time'][:])
tall = np.datetime64('1981-01-01T00:00:00') + traw.astype('timedelta64[s]')

j = int(np.where(tall == np.datetime64('2010-07-15'))[0][0])
k = int(np.where(tt == np.datetime64('2010-07-15'))[0][0])
remote = np.asarray(v[j, 157:217, 562:622])
saved = target[k]
both = np.isnan(remote) & np.isnan(saved)
neq = (remote != saved) & ~both
ys, xs = np.where(neq)
print("n non-NaN mismatches:", len(ys))
for i in range(min(8, len(ys))):
    print(" ", ys[i], xs[i], repr(remote[ys[i], xs[i]]), repr(saved[ys[i], xs[i]]),
          "u32:", np.float32(remote[ys[i],xs[i]]).view(np.uint32), np.float32(saved[ys[i],xs[i]]).view(np.uint32))
