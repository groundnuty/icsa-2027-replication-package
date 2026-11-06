
import xarray as xr
import numpy as np
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")
v = ds.analysed_sst
print("var attrs:", dict(v.attrs))
lat = ds.latitude.values
lon = ds.longitude.values
print("lat min/max", lat.min(), lat.max(), "dlat", np.diff(lat)[:5])
print("lon min/max", lon.min(), lon.max(), "dlon", np.diff(lon)[:5])

latm = (lat >= 56.63) & (lat <= 57.83)
lonm = (lon >= 20.23) & (lon <= 21.43)
print("n lat cells:", latm.sum(), lat[latm][:5], lat[latm][-5:])
print("n lon cells:", lonm.sum(), lon[lonm][:5], lon[lonm][-5:])

# time indices for needed ranges
t = ds.time.values
t0 = t[0]; tN = t[-1]
def idx(d): 
    import numpy as np
    return int(np.searchsorted(t, np.datetime64(d)))
print("time step check:", t[1]-t[0])
need_start = "1991-12-27"; need_end="2003-01-05"
tg0="2010-06-01"; tg1="2010-08-31"
i0 = idx(need_start); i1 = idx(need_end)
j0 = idx(tg0); j1 = idx(tg1)
print("idx", i0, i1, t[i0], t[i1], j0, j1, t[j0], t[j1])
# ensure contiguous
print("baseline span days:", i1-i0+1, "target span days:", j1-j0+1)
