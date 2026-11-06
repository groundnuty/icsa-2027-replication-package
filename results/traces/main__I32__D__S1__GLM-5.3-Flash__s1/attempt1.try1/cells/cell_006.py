import xarray as xr
import h5netcdf
with h5netcdf.File('/work/sst_s2.nc','r') as f:
    print("dims:", dict(f.dimensions))
    print("vars:", list(f.variables.keys()))
    for k,v in f.variables.items():
        print(k, dict(v.dimensions), v.shape, v.dtype)
    print("global attrs:", {k: f.attrs[k] for k in f.attrs})
