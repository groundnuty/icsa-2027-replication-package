import fsspec, xarray as xr, numpy as np, pickle, time, datetime as dt

fs = fsspec.filesystem('onedata')
f = fs.open("icsa2027_data_20261101T090944Z/s2z/sst_s2.nc", "rb")
ds = xr.open_dataset(f, engine="h5netcdf")
v = ds["analysed_sst"]

lat = ds.latitude.values; lon = ds.longitude.values
latm = (lat >= 57.33) & (lat <= 58.53)
lonm = (lon >= 9.03) & (lon <= 10.23)
lat_idx = np.flatnonzero(latm); lon_idx = np.flatnonzero(lonm)
lat_sel = lat[latm]; lon_sel = lon[lonm]
print("region:", lat_sel[0], lat_sel[-1], lon_sel[0], lon_sel[-1], lat_sel.size, lon_sel.size)

tall = ds.time.values  # datetime64[ns]
def dates_between(y0,m0,d0,y1,m1,d1):
    out=[]; cur=dt.date(y0,m0,d0); end=dt.date(y1,m1,d1)
    while cur<=end: out.append(cur); cur+=dt.timedelta(days=1)
    return out
base_dates = dates_between(1991,12,27,2003,1,5)
tgt_dates  = dates_between(2012,6,1,2012,8,31)
print("base days:", len(base_dates), "tgt days:", len(tgt_dates))

def idx_of(d):
    return int((np.datetime64(d.isoformat()) - tall[0]) // np.timedelta64(1,'D'))
base_idx = np.array([idx_of(d) for d in base_dates])
tgt_idx  = np.array([idx_of(d) for d in tgt_dates])
# verify contiguity of indices
print("base idx range:", base_idx.min(), base_idx.max(), "contig:", np.all(np.diff(base_idx)==1))
print("tgt idx range:", tgt_idx.min(), tgt_idx.max(), "contig:", np.all(np.diff(tgt_idx)==1))

t0=time.time()
B = v.values[base_idx[:,None,None], lat_idx[:,None], lon_idx].astype(np.float64) if False else None
# do per-date reads to keep requests small
B = np.empty((len(base_idx), lat_sel.size, lon_sel.size), dtype=np.float64)
for k in range(len(base_idx)):
    B[k] = v.values[base_idx[k]][lat_idx[:,None], lon_idx]
print("base load done in %.1fs" % (time.time()-t0), B.shape)
T = np.empty((len(tgt_idx), lat_sel.size, lon_sel.size), dtype=np.float64)
t0=time.time()
for k in range(len(tgt_idx)):
    T[k] = v.values[tgt_idx[k]][lat_idx[:,None], lon_idx]
print("target load done in %.1fs" % (time.time()-t0), T.shape)
print("base finite frac:", np.isfinite(B).mean(), "tgt finite frac:", np.isfinite(T).mean())
pickle.dump({"B":B,"T":T,"base_dates":base_dates,"tgt_dates":tgt_dates,
             "lat_sel":lat_sel,"lon_sel":lon_sel,
             "base_idx":base_idx,"tgt_idx":tgt_idx}, open("/tmp/mhw_data.pkl","wb"))
f.close()
print("saved")