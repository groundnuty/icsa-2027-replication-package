import xarray as xr, numpy as np, pickle, os
from datetime import date, timedelta
base = "/data/icsa2027_data_20261101T090944Z/s1z"
meta = pickle.load(open("/tmp/target.pkl","rb"))
lat, lon = meta["lat"], meta["lon"]
slat, slon = meta["slat"], meta["slon"]

# 1) verify file time coords match filenames for a sample
for f, d in [("sst_20170715.nc", date(2017,7,15)), ("sst_20170601.nc", date(2017,6,1)),
             ("sst_20170831.nc", date(2017,8,31)), ("sst_19960715.nc", date(1996,7,15))]:
    ds = xr.open_dataset(os.path.join(base,f), engine="h5netcdf")
    t = ds.time.values[0]
    ok = t == np.datetime64(d.isoformat())
    print(f, "->", str(t), "match:", ok)
    ds.close()

# 2) raw value check: cell (62.96, 18.74) on 2017-07-15
ds = xr.open_dataset(os.path.join(base,"sst_20170715.nc"), engine="h5netcdf")
v = ds["analysed_sst"].values.astype("float64")[0]
il = np.flatnonzero(slat)[np.argmin(np.abs(lat[slat]-62.96))]
ik = np.flatnonzero(slon)[np.argmin(np.abs(lon[slon]-18.74))]
print("raw value 62.96/18.74 2017-07-15:", v[il, ik], " (expect 286.74)")
ds.close()

# 3) manual pool for doy 197 (Jul 15) for that cell
tc = pickle.load(open("/tmp/thrclim.pkl","rb"))
X = np.load("/tmp/X.npy")
Xd = X.reshape(4028, 3600)
c = il*60 + ik
pools = pickle.load(open("/tmp/pools.pkl","rb"))
dates_all = pickle.load(open("/tmp/pools.pkl","rb"))["dates"]
idx = pools[197]
print("pool n dates:", len(idx))
vals = Xd[idx, c]
print("pool finite:", int(np.isfinite(vals).sum()), "of", len(vals))
print("manual hazen90:", np.nanquantile(vals, 0.9, method="hazen"))
print("stored raw thr[196,c]:", tc["thr_raw"][196, c])
print("pool date range:", dates_all[idx[0]], dates_all[idx[-1]])
print("pool stats: min %.2f max %.2f mean %.2f" % (np.nanmin(vals), np.nanmax(vals), np.nanmean(vals)))
