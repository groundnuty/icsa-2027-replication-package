import numpy as np, datetime as dt, fsspec, h5py, time, warnings
print("numpy", np.__version__)

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# --- grid selection ---
with fs.open(f"{base}/sst_20120601.nc",'rb') as f:
    with h5py.File(f,'r') as h:
        lat = h['latitude'][:]; lon = h['longitude'][:]
        t2012 = h['time'][0]

with fs.open(f"{base}/sst_19920601.nc",'rb') as f:
    with h5py.File(f,'r') as h:
        lat2 = h['latitude'][:]; lon2 = h['longitude'][:]

print("grids identical across years:", np.array_equal(lat, lat2), np.array_equal(lon, lon2))
latf = lat.astype(np.float64); lonf = lon.astype(np.float64)
latm = (latf >= 54.45) & (latf <= 55.65)
lonm = (lonf >= 16.05) & (lonf <= 17.25)
lat_idx = np.where(latm)[0]; lon_idx = np.where(lonm)[0]
print("lat idx:", lat_idx.min(), lat_idx.max(), lat_idx.size)
print("lon idx:", lon_idx.min(), lon_idx.max(), lon_idx.size)
print("lat values:", lat[lat_idx[0]], "...", lat[lat_idx[-1]])
print("lon values:", lon[lon_idx[0]], "...", lon[lon_idx[-1]])
print("next outside:", lat[lat_idx.min()-1], lat[lat_idx.max()+1], lon[lon_idx.min()-1], lon[lon_idx.max()+1])
lat0,lat1 = lat_idx.min(), lat_idx.max()+1
lon0,lon1 = lon_idx.min(), lon_idx.max()+1
print("slices:", lat0,lat1,lon0,lon1, "shape:", lat1-lat0, lon1-lon0)

# --- doy mapping ---
def doy366(d):
    if d.month == 2 and d.day == 29:
        return 60
    if d.month <= 2:
        return (d - dt.date(d.year,1,1)).days + 1
    return 61 + (d - dt.date(d.year,3,1)).days

tests = [(dt.date(1992,1,1),1),(dt.date(1992,2,28),59),(dt.date(1992,2,29),60),
         (dt.date(1992,3,1),61),(dt.date(1991,3,1),61),(dt.date(1991,2,28),59),
         (dt.date(1991,12,31),366),(dt.date(1992,12,31),366),(dt.date(1993,3,1),61),
         (dt.date(1993,12,31),366),(dt.date(2012,6,1),61+(dt.date(2012,6,1)-dt.date(2012,3,1)).days)]
for d,e in tests:
    v = doy366(d)
    assert v==e, (d,v,e)
print("doy mapping OK; 2012-06-01 ->", doy366(dt.date(2012,6,1)), " 2012-08-31 ->", doy366(dt.date(2012,8,31)))

# --- time encoding check ---
ref = np.datetime64('1981-01-01T00:00:00')
print("2012-06-01 file time ->", ref + np.timedelta64(int(t2012),'s'))

# --- benchmark nanpercentile hazen ---
rng = np.random.default_rng(0)
pool = rng.random((121,60,60))
pool[0,0,0] = np.nan
t0=time.time()
r = np.nanpercentile(pool, 90, axis=0, method='hazen')
print("nanpercentile (121,60,60) sec:", time.time()-t0)
# sanity hazen vs manual on 1D
x = np.array([1.,2,3,4,5,6,7,8,9,10])
q = np.percentile(x, 90, method='hazen')
h = 0.9*(len(x)+1)  # hazen plotting position: p*(n+1)? check
print("hazen 1D:", q)
