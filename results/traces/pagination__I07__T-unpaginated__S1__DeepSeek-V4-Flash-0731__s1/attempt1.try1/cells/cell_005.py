
import fsspec
import xarray as xr
import numpy as np

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    lats = ds.latitude.values
    lons = ds.longitude.values
    print("Lat range:", lats.min(), lats.max(), "step:", lats[1]-lats[0])
    print("Lon range:", lons.min(), lons.max(), "step:", lons[1]-lons[0])
    # Find region indices
    lat_mask = (lats >= 54.45) & (lats <= 55.65)
    lon_mask = (lons >= 16.05) & (lons <= 17.25)
    lat_idx = np.where(lat_mask)[0]
    lon_idx = np.where(lon_mask)[0]
    print("Lat indices in region:", lat_idx[0], "to", lat_idx[-1], "count:", len(lat_idx))
    print("Lon indices in region:", lon_idx[0], "to", lon_idx[-1], "count:", len(lon_idx))
    print("Region lat values:", lats[lat_idx])
    print("Region lon values:", lons[lon_idx])
    # Print the SST values for the region on this day
    sst = ds.analysed_sst.values[0, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1]
    print("SST shape:", sst.shape)
    print("SST values (first few):", sst.flatten()[:10])
    print("NaN count:", np.isnan(sst).sum())
