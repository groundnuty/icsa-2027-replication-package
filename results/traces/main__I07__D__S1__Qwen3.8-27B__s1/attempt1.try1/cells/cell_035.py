import xarray as xr, numpy as np
from datetime import date, timedelta
lat_vals = np.load('/work/lat_vals.npy'); lon_vals = np.load('/work/lon_vals.npy')
ci, cj = 30, 30

def read_region(dt):
    p = f"/work/data/sst_{dt.year:04d}{dt.month:02d}{dt.day:02d}.nc"
    d2 = xr.open_dataset(p, engine='h5netcdf')
    a = d2['analysed_sst'].values[0]; la = d2.latitude.values; lo = d2.longitude.values
    d2.close()
    mi = np.where(la == np.float32(float(lat_vals[ci])))[0]
    mj = np.where(lo == np.float32(float(lon_vals[cj])))[0]
    assert len(mi) == 1 and len(mj) == 1, (len(mi), len(mj))
    return float(a[mi[0], mj[0]])

try:
    v = read_region(date(1992,5,27))
    print("1992-05-27:", v)
except Exception as e:
    print("ERR", type(e).__name__, e)
    d2 = xr.open_dataset('/work/data/sst_19920527.nc', engine='h5netcdf')
    la = d2.latitude.values; lo = d2.longitude.values
    mi = np.where(la == np.float32(float(lat_vals[30])))[0]
    mj = np.where(lo == np.float32(float(lon_vals[30])))[0]
    print("mi:", mi, "mj:", mj)
    print("la sample:", la[78:80], "lat_vals[30]:", lat_vals[30])
    print("lo sample:", lo[352:354], "lon_vals[30]:", lon_vals[30])
    d2.close()
