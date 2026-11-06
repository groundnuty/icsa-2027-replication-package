
import fsspec
import xarray as xr
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    # Check lat/lon ranges
    print("Lat range:", ds.latitude.values.min(), ds.latitude.values.max())
    print("Lon range:", ds.longitude.values.min(), ds.longitude.values.max())
    print("Time range:", ds.time.values[0], ds.time.values[-1])
    print("Time step:", ds.time.values[1] - ds.time.values[0])
    # Check what lat/lon values are near our region
    lat_vals = ds.latitude.values
    lon_vals = ds.longitude.values
    print("Lats in region:", lat_vals[(lat_vals >= 56.09) & (lat_vals <= 57.29)])
    print("Lons in region:", lon_vals[(lon_vals >= 10.55) & (lon_vals <= 11.75)])
    print("Num lats in region:", len(lat_vals[(lat_vals >= 56.09) & (lat_vals <= 57.29)]))
    print("Num lons in region:", len(lon_vals[(lon_vals >= 10.55) & (lon_vals <= 11.75)]))
