import xarray as xr
p="/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds=xr.open_dataset(p,engine="h5netcdf");print(ds)
print(ds.time.values[[0,-1]],ds.lat.values[[0,-1]],ds.lon.values[[0,-1]])