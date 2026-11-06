import xarray as xr
import fsspec

fs = fsspec.filesystem('onedata')
# Open one file to understand the structure
with fs.open('/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc', 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print("SST variable details:")
    print(ds['analysed_sst'])
    print("\nLatitude range:", ds.latitude.min().values, "to", ds.latitude.max().values)
    print("Longitude range:", ds.longitude.min().values, "to", ds.longitude.max().values)
    ds.close()