import xarray as xr, numpy as np
p = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(p, engine="h5netcdf")
lat = ds.latitude.values; lon = ds.longitude.values; t = ds.time.values
print("lat range", lat.min(), lat.max(), "n", lat.size)
print("lon range", lon.min(), lon.max(), "n", lon.size)
print("time", t[0], t[-1], "n", t.size)
# check daily continuity
d = np.diff(t).astype('timedelta64[D]').astype(int)
print("time step unique:", np.unique(d))
# region indices (float32 coords vs float64 bounds: exact compare fine since values like 21.25 representable? 21.25 yes; 59.05 not exactly in float32 but bounds inclusive on grid values; find via tolerance)
def idx_range(arr, lo, hi):
    m = (arr >= lo - 1e-6) & (arr <= hi + 1e-6)
    i = np.where(m)[0]
    return i[0], i[-1], m.sum()
print("lat idx", idx_range(lat, 59.05, 60.25))
print("lon idx", idx_range(lon, 21.25, 22.45))
# print actual boundary values
i0,i1,n = idx_range(lat,59.05,60.25); print(lat[i0], lat[i1])
j0,j1,n2 = idx_range(lon,21.25,22.45); print(lon[j0], lon[j1])
print("region cells", (i1-i0+1)*(j1-j0+1))
# check encoding of analysed_sst
print(ds.analysed_sst.encoding)
