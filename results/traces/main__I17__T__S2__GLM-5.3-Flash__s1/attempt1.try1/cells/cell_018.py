import numpy as np, fsspec, h5netcdf

me = '/work/me/'
target = np.load(me+'target.npy')
base = np.load(me+'base.npy')
tt = np.load(me+'times_target.npy'); tb = np.load(me+'times_base.npy')
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','rb')
nc = h5netcdf.File(f,'r'); v = nc['analysed_sst']
traw = np.asarray(nc['time'][:])
tall = np.datetime64('1981-01-01T00:00:00') + traw.astype('timedelta64[s]')

def check(tref, sub, ttarr):
    j = int(np.where(tall == np.datetime64(tref))[0][0])
    k = int(np.where(ttarr == np.datetime64(tref))[0][0])
    remote = np.asarray(v[j, 157:217, 562:622])
    saved = sub[k]
    both_nan = np.isnan(remote) & np.isnan(saved)
    neq = (remote != saved) & ~both_nan
    one_nan = np.isnan(remote) ^ np.isnan(saved)
    print(tref, "equal_nan:", np.array_equal(remote, saved, equal_nan=True),
          "| non-NaN mismatches:", int(neq.sum()), "| NaN-pattern mismatches:", int(one_nan.sum()))
    if neq.sum() or one_nan.sum():
        ys, xs = np.where(neq | one_nan)
        print("  ex:", ys[0], xs[0], remote[ys[0],xs[0]], saved[ys[0],xs[0]])

check('2010-07-15', target, tt)
check('2010-06-01', target, tt)
check('2010-08-31', target, tt)
check('1997-03-08', base, tb)
check('1992-01-01', base, tb)
check('2003-01-05', base, tb)
check('1999-07-20', base, tb)
