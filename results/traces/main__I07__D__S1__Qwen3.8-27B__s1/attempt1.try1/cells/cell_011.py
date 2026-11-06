import xarray as xr, numpy as np, time
from datetime import date, timedelta

# region masks from one file's coords (consistent across files; verify on the fly)
ref = xr.open_dataset('/work/data/sst_20210601.nc', engine='h5netcdf')
lat_all = ref.latitude.values; lon_all = ref.longitude.values
lm = (lat_all >= 54.45) & (lat_all <= 55.65)
mm = (lon_all >= 16.05) & (lon_all <= 17.25)
lat_idx = np.where(lm)[0]; lon_idx = np.where(mm)[0]
lat_vals = lat_all[lat_idx]; lon_vals = lon_all[lon_idx]
ref.close()
print("region shape:", lat_vals.size, lon_vals.size)

def fname(dt): return f"sst_{dt.year:04d}{dt.month:02d}{dt.day:02d}.nc"

def load_one(path):
    ds = xr.open_dataset(path, engine='h5netcdf')
    a = ds['analysed_sst'].values[0]  # (lat, lon)
    tval = ds['time'].values[0]
    la = ds['latitude'].values; lo = ds['longitude'].values
    if la.shape != lat_all.shape or not np.array_equal(la, lat_all) or not np.array_equal(lo, lon_all):
        ds.close()
        raise RuntimeError("grid mismatch")
    ds.close()
    return a[np.ix_(lat_idx, lon_idx)].astype(np.float64), np.datetime64(tval)

# baseline range
base_dates = []
d = date(1991,12,27)
while d <= date(2003,1,5):
    base_dates.append(d); d += timedelta(days=1)
tgt_dates = []
d = date(2021,6,1)
while d <= date(2021,8,31):
    tgt_dates.append(d); d += timedelta(days=1)

t0 = time.time()
S_base = np.empty((len(base_dates), lat_vals.size, lon_vals.size), dtype=np.float64)
times_base = np.empty(len(base_dates), dtype='datetime64[ns]')
for i, dt in enumerate(base_dates):
    a, tv = load_one(f"/work/data/{fname(dt)}")
    S_base[i] = a; times_base[i] = tv
print("baseline load:", round(time.time()-t0,1), "s")

t0 = time.time()
S_tgt = np.empty((len(tgt_dates), lat_vals.size, lon_vals.size), dtype=np.float64)
times_tgt = np.empty(len(tgt_dates), dtype='datetime64[ns]')
for i, dt in enumerate(tgt_dates):
    a, tv = load_one(f"/work/data/{fname(dt)}")
    S_tgt[i] = a; times_tgt[i] = tv
print("target load:", round(time.time()-t0,1), "s")

np.save('/work/S_base.npy', S_base)
np.save('/work/S_tgt.npy', S_tgt)
np.save('/work/lat_vals.npy', lat_vals)
np.save('/work/lon_vals.npy', lon_vals)
print("S_base", S_base.shape, S_base.dtype, "finite frac", np.isfinite(S_base).mean())
print("S_tgt", S_tgt.shape, "finite frac", np.isfinite(S_tgt).mean())
print("base date check:", times_base[0], times_base[-1], "tgt:", times_tgt[0], times_tgt[-1])
# check times consistent with dates
ok = all(np.datetime64(f'{dt}') == times_base[i] for i, dt in enumerate(base_dates[:5]))
print("time consistency ok:", ok)
ok2 = all(np.datetime64(f'{dt}') == times_tgt[i] for i, dt in enumerate(tgt_dates[:5]))
print("tgt time ok:", ok2)
