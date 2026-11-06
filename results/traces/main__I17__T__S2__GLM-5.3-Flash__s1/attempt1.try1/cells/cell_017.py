import numpy as np, fsspec, h5netcdf

me = '/work/me/'
target = np.load(me+'target.npy')
tt = np.load(me+'times_target.npy')
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','rb')
nc = h5netcdf.File(f,'r'); v = nc['analysed_sst']
traw = np.asarray(nc['time'][:])
tall = np.datetime64('1981-01-01T00:00:00') + traw.astype('timedelta64[s]')
print("2010-07-15 in tall?", np.datetime64('2010-07-15') in tall)
j = int(np.where(tall == np.datetime64('2010-07-15'))[0][0])
k = int(np.where(tt == np.datetime64('2010-07-15'))[0][0])
print("j=", j, "k=", k, "tt[k]=", tt[k])
remote = np.asarray(v[j, 157:217, 562:622])
saved = target[k]
print("equal:", np.array_equal(remote, saved))
diff = remote != saved
print("n differing cells:", diff.sum(), "of", diff.size)
if diff.sum():
    ys, xs = np.where(diff)
    print("example diff at", ys[0], xs[0], remote[ys[0], xs[0]], saved[ys[0], xs[0]])
# also compare full chunk row region to rule out slicing issues
full = np.asarray(v[j, :, :])
print("full[157:217,562:622] == saved:", np.array_equal(full[157:217, 562:622], saved))
print("full[157:217,562:622] == remote:", np.array_equal(full[157:217, 562:622], remote))
