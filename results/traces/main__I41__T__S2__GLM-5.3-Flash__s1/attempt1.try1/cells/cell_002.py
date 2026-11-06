import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    lat = ds['latitude'].values
    lon = ds['longitude'].values
    print("lat first/last:", lat[0], lat[-1])
    print("lon first/last:", lon[0], lon[-1])
    dlat = np.diff(lat); dlon = np.diff(lon)
    print("dlat uniq (rounded):", np.unique(np.round(dlat,7))[:10])
    print("dlon uniq (rounded):", np.unique(np.round(dlon,7))[:10])
    print("lat monotonic increasing:", np.all(dlat>0), " lon monotonic increasing:", np.all(dlon>0))
    # time
    t = ds['time'].values
    print("time regular daily:", np.all(np.diff(t.astype('datetime64[D]').astype(np.int64))==1))
    print("time attrs:", ds['time'].attrs)
    print("lat attrs:", ds['latitude'].attrs)
    print("lon attrs:", ds['longitude'].attrs)

# storage layout via h5py
import h5py
with fs.open(path, 'rb') as f:
    with h5py.File(f, 'r') as h5:
        def show(name, obj):
            if isinstance(obj, h5py.Dataset):
                print(name, obj.shape, obj.dtype, "chunks:", obj.chunks, "compression:", obj.compression)
        h5.visititems(show)
