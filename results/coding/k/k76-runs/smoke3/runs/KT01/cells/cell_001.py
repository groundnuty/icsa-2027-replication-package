import os
import fsspec, xarray as xr
fs = fsspec.filesystem("onedata")
with fs.open(os.environ["ICSA_DATASET_LOCATION"], "rb") as fh:
    with xr.open_dataset(fh, engine="h5netcdf", decode_times=False) as ds:
        print(dict(ds.sizes))
