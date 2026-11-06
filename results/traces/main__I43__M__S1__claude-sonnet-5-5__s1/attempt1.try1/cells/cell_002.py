import xarray as xr
p='/data/icsa2027_data_20261101T090944Z/s1z/sst_20170601.nc'
d=xr.open_dataset(p,engine='h5netcdf');print(d)
fs=sorted(os.listdir(os.path.dirname(p)));print(len(fs))
import datetime
ds=[f[4:12] for f in fs];print(ds[0],ds[-1])