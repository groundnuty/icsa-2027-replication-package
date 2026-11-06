
import xarray as xr
p="/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
d=xr.open_dataset(p,engine="h5netcdf")
print(d)
t=d.time.values;print(t[0],t[-1],len(t))
