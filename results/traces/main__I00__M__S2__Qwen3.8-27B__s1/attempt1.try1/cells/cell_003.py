import numpy as np, xarray
ds = xarray.open_dataset("/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc", engine="h5netcdf")
v = ds.analysed_sst
print("var attrs:")
for k,val in v.attrs.items():
    print(" ", k, "=", str(val)[:300])
print()
print("time attrs:", ds.time.attrs)
print("lat attrs:", ds.latitude.attrs)
print("lon attrs:", ds.longitude.attrs)

lat = ds.latitude.values
lon = ds.longitude.values
print("lat min/max:", lat.min(), lat.max(), "n=", len(lat))
print("lon min/max:", lon.min(), lon.max(), "n=", len(lon))

sel_lat = (lat >= 54.13) & (lat <= 55.33)
sel_lon = (lon >= 14.67) & (lon <= 15.87)
print("n lat in region:", int(sel_lat.sum()), "first/last:", lat[sel_lat][[0,-1]])
print("n lon in region:", int(sel_lon.sum()), "first/last:", lon[sel_lon][[0,-1]])
print("total cells:", int(sel_lat.sum()*sel_lon.sum()))

t = ds.time.values
dt = np.diff(t.astype('datetime64[D]'))
print("time diffs unique:", len(np.unique(dt)), dt.min(), dt.max())
print("first/last time:", t[0], t[-1])
for d in ["1991-12-27","1992-01-01","2002-12-31","2003-01-05","2004-06-01","2004-08-31"]:
    i = np.where(t == np.datetime64(d))[0]
    print(d, "->", i)
