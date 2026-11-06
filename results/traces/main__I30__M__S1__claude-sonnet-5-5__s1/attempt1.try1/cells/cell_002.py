import xarray as xr
p='/data/icsa2027_data_20261101T090944Z/s1z/sst_20100601.nc'
d=xr.open_dataset(p,engine='h5netcdf');print(d)
import glob
fs=sorted(glob.glob('/data/icsa2027_data_20261101T090944Z/s1z/*.nc'));print(len(fs))