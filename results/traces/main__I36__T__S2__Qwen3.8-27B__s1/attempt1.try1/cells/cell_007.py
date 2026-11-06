import fsspec, numpy as np, xarray as xr, warnings, traceback
from datetime import date

fs = fsspec.filesystem('onedata')
PATH = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f = fs.open(PATH, 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
latv = ds.latitude.values.astype(np.float64); lonv = ds.longitude.values.astype(np.float64)
mlat = (latv>=60.09)&(latv<=61.29); mlon = (lonv>=20.01)&(lonv<=21.21)
LA, LO = int(mlat.sum()), int(mlon.sum())
t = ds.time.values
mt = (t>=np.datetime64('1991-12-27'))&(t<=np.datetime64('2003-08-31'))
dts = t[mt].astype('datetime64[D]').astype(object)
T = len(dts); ord_ = np.array([d.toordinal() for d in dts])
sub = ds.analysed_sst.isel(time=mt, latitude=mlat, longitude=mlon).values.astype(np.float64)
cum = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
mm = np.array([d.month for d in dts]); dd = np.array([d.day for d in dts])
doy = cum[mm-1] + dd
inb = (ord_ >= date(1992,1,1).toordinal()) & (ord_ <= date(2002,12,31).toordinal())
C = LA*LO
print('T', T, 'C', C)
thr = np.full((366, C), np.nan)
for d in range(1, 367):
    if d == 60: continue
    bm = (doy==d) & inb
    pm = np.zeros(T, bool)
    for k in range(-5, 6):
        if k >= 0: pm[k:] |= bm[:T-k]
        else:      pm[:T+k] |= bm[-k:]
    pool = sub[pm].reshape(-1, C)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            q = np.nanquantile(pool, 0.9, axis=0, method='hazen')
        thr[d] = q
        if d % 50 == 0 or int(pm.sum()) != 121:
            print('d', d, 'pool', pool.shape, 'pm.sum', int(pm.sum()))
    except Exception:
        print('FAILED at d =', d, 'pool shape', pool.shape, 'pm.sum', int(pm.sum()))
        traceback.print_exc()
        break
else:
    print('loop finished, thr sample thr[196,:3]', thr[196,:3])
ds.close(); f.close()
