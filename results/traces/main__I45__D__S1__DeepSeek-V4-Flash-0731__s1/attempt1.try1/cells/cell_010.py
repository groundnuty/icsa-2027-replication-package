
import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print("Time range:", ds['time'].values[0], "to", ds['time'].values[-1])
print("Time count:", len(ds['time']))
print("Lat range:", ds['latitude'].values[0], "to", ds['latitude'].values[-1])
print("Lon range:", ds['longitude'].values[0], "to", ds['longitude'].values[-1])
print("Lat count:", len(ds['latitude']))
print("Lon count:", len(ds['longitude']))
print("Variable:", ds['analysed_sst'].dtype)
ds.close()
