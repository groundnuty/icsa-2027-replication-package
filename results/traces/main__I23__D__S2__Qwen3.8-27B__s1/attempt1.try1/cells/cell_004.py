import xarray as xr
import numpy as np
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat = ds.latitude.values  # float32
lon = ds.longitude.values
t = ds.time.values

# region bounds inclusive
lat_i = np.where((lat >= 57.41) & (lat <= 58.61))[0]
lon_i = np.where((lon >= 18.69) & (lon <= 19.89))[0]
print("n lat:", lat_i.size, lat_i[0], lat_i[-1], lat[lat_i[0]], lat[lat_i[-1]])
print("n lon:", lon_i.size, lon_i[0], lon_i[-1], lon[lon_i[0]], lon[lon_i[-1]])
# check spacing / no gaps
print("lat diffs ok:", np.all(np.diff(lat_i)==1), "lon diffs ok:", np.all(np.diff(lon_i)==1))

# time index for needed windows
t64 = t.astype('datetime64[D]')
def idx(dstr):
    return int(np.searchsorted(t64, np.datetime64(dstr)))
print("target start idx:", idx('2013-06-01'), t[idx('2013-06-01')])
print("target end idx:", idx('2013-08-31'), t[idx('2013-08-31')])
print("win start idx:", idx('1991-12-27'), t[idx('1991-12-27')])
print("win end idx:", idx('2003-01-05'), t[idx('2003-01-05')])
print("base start idx:", idx('1992-01-01'), t[idx('1992-01-01')])
print("base end idx:", idx('2002-12-31'), t[idx('2002-12-31')])
