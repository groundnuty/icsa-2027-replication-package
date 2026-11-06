import xarray as xr
p="/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
d=xr.open_dataset(p,engine="h5netcdf")
print(d)
print(d.time.values[[0,-1]])