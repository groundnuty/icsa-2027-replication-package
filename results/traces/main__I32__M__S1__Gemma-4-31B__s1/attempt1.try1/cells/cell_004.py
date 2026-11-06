import xarray as xr

sample_file = '/data/icsa2027_data_20261101T090944Z/s1z/sst_20231231.nc'
ds = xr.open_dataset(sample_file, engine="h5netcdf")
print(f"Lat range: {ds.latitude.min().values} to {ds.latitude.max().values}, step {ds.latitude[1].values - ds.latitude[0].values}")
print(f"Lon range: {ds.longitude.min().values} to {ds.longitude.max().values}, step {ds.longitude[1].values - ds.longitude[0].values}")
