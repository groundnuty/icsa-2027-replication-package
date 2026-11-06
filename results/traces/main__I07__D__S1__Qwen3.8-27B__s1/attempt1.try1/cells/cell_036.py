import xarray as xr, numpy as np
from datetime import date, timedelta
lat_vals = np.load('/work/lat_vals.npy'); lon_vals = np.load('/work/lon_vals.npy')
ci, cj = 30, 30
import time; t0=time.time()

def read_region(dt):
    p = f"/work/data/sst_{dt.year:04d}{dt.month:02d}{dt.day:02d}.nc"
    d2 = xr.open_dataset(p, engine='h5netcdf')
    a = d2['analysed_sst'].values[0]; la = d2.latitude.values; lo = d2.longitude.values
    d2.close()
    mi = np.where(la == np.float32(float(lat_vals[ci])))[0]
    mj = np.where(lo == np.float32(float(lon_vals[cj])))[0]
    if len(mi) != 1 or len(mj) != 1:
        raise RuntimeError(f"{dt}: mi={mi} mj={mj}")
    return float(a[mi[0], mj[0]])

def doy_of(dt): return (date(2000, dt.month, dt.day) - date(2000,1,1)).days + 1

def pool_for_doy_cell(dd):
    md = date(2000,1,1) + timedelta(days=dd-1)
    vals = []
    for y in range(1992, 2003):
        b = date(y, md.month, md.day)
        for k in range(-5, 6):
            vals.append(read_region(b + timedelta(days=k)))
    return np.array(vals)

q153 = np.quantile(pool_for_doy_cell(153), 0.9, method='hazen')
raw_thr = np.array([np.quantile(pool_for_doy_cell(dd), 0.9, method='hazen') for dd in range(138, 169)])
thr_smooth_153 = raw_thr.mean()
thr_s = np.load('/work/thr_s.npy')
saved = thr_s[153-1, ci*60+cj]
print("independent smoothed thr (cell 30,30, doy153):", thr_smooth_153)
print("saved thr_s:", saved, " MATCH:", np.isclose(thr_smooth_153, saved))

mask = np.load('/work/mask.npy'); S_tgt = np.load('/work/S_tgt.npy')
print()
for dt in [date(2021,6,1), date(2021,6,2), date(2021,6,3), date(2021,6,4), date(2021,6,5), date(2021,6,6)]:
    sst = read_region(dt)
    t = thr_s[doy_of(dt)-1, ci*60+cj]
    print(dt, "sst:", sst, "thr:", round(t,4), "hot:", sst >= t, "| mask:", mask[(dt-date(2021,6,1)).days, ci, cj])
print("elapsed:", round(time.time()-t0,1), "s")
