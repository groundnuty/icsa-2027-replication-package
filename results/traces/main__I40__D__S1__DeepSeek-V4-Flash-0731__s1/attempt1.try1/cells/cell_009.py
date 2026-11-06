
import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
# Check lat/lon range
print("Latitude range:", ds.latitude.values[0], "to", ds.latitude.values[-1])
print("Longitude range:", ds.longitude.values[0], "to", ds.longitude.values[-1])
print("Time range:", ds.time.values[0], "to", ds.time.values[-1])
print("Data var:", list(ds.data_vars.keys()))
print("Units:", ds.analysed_sst.attrs)
print("Lat resolution:", ds.latitude.values[1] - ds.latitude.values[0])
print("Lon resolution:", ds.longitude.values[1] - ds.longitude.values[0])

# Check what's in our region
# lat 61.57 to 62.77, lon 20.17 to 21.37
lat_mask = (ds.latitude.values >= 61.57) & (ds.latitude.values <= 62.77)
lon_mask = (ds.longitude.values >= 20.17) & (ds.longitude.values <= 21.37)
print(f"Lat indices in region: {ds.latitude.values[lat_mask]}")
print(f"Lon indices in region: {ds.longitude.values[lon_mask]}")
print(f"Num lat in region: {lat_mask.sum()}")
print(f"Num lon in region: {lon_mask.sum()}")
