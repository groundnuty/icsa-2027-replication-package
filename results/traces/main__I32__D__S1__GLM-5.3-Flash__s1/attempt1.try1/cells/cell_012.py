import numpy as np, h5py, time as _time, os, json
from datetime import date, timedelta

f = h5py.File('/work/sst_s2.nc','r')
lat = f['latitude'][:]; lon = f['longitude'][:]
latr = np.round(lat.astype(np.float64), 6); lonr = np.round(lon.astype(np.float64), 6)
ilats = np.where((latr >= 59.05) & (latr <= 60.25))[0]
ilons = np.where((lonr >= 21.25) & (lonr <= 22.45))[0]
la0, la1 = ilats[0], ilats[-1]+1
lo0, lo1 = ilons[0], ilons[-1]+1
tv = f['time'][:].astype(np.int64)
days_since = tv // 86400
epoch = date(1981,1,1)
file_start_idx = int(days_since[0]) - (date(1982,1,1)-epoch).days  # array index of 1982-01-01 = 0
# array index of a date:
def arr_idx(d): return (d - date(1982,1,1)).days

b0, b1 = date(1991,12,27), date(2003,1,5)
t0d, t1d = date(2005,6,1), date(2005,8,31)
ib0, ib1 = arr_idx(b0), arr_idx(b1)
it0, it1 = arr_idx(t0d), arr_idx(t1d)
print("baseline idx", ib0, ib1, "target idx", it0, it1)

d = f['analysed_sst']
t1=_time.time()
B = d[ib0:ib1+1, la0:la1, lo0:lo1].astype(np.float64)
T = d[it0:it1+1, la0:la1, lo0:lo1].astype(np.float64)
print("read time", _time.time()-t1, "B", B.shape, "T", T.shape)
# dates arrays
nb = (b1-b0).days + 1
bdates = [b0 + timedelta(days=i) for i in range(nb)]
tdates = [t0d + timedelta(days=i) for i in range((t1d-t0d).days+1)]
# verify dates align with file
chk = all((epoch + timedelta(days=int(days_since[ib0+i]))) == bdates[i] for i in range(nb))
chk2 = all((epoch + timedelta(days=int(days_since[it0+i]))) == tdates[i] for i in range(len(tdates)))
print("date alignment:", chk, chk2)
print("B finite frac", np.isfinite(B).mean(), "T finite frac", np.isfinite(T).mean())
np.save('/work/B.npy', B); np.save('/work/T.npy', T)
with open('/work/meta.json','w') as fh:
    json.dump({'b0':str(b0),'b1':str(b1),'t0':str(t0d),'t1':str(t1d),
               'la0':int(la0),'la1':int(la1),'lo0':int(lo0),'lo1':int(lo1),
               'lat_vals':lat[la0:la1].tolist(),'lon_vals':lon[lo0:lo1].tolist(),
               'time_secs_baseline':tv[ib0:ib1+1].tolist(),'time_secs_target':tv[it0:it1+1].tolist()}, fh)
print("saved")
