import h5py, numpy as np, time
p = "/data/icsa2027_data_20261101T090944Z/s1z/sst_20130601.nc"
t0=time.time()
with h5py.File(p, "r") as f:
    print(list(f.keys()))
    d = f["analysed_sst"]
    print(d.shape, d.dtype, dict(d.attrs))
    sub = d[0, 218:278, 601:661]
print("read time:", time.time()-t0, "sub stats:", sub.shape, np.isfinite(sub).sum(), sub.min(), sub.max())
# check grid identical across a few sample files
import xarray as xr
for fn in ["sst_19920201.nc","sst_20021231.nc","sst_20230615.nc"]:
    ds = xr.open_dataset("/data/icsa2027_data_20261101T090944Z/s1z/"+fn, engine="h5netcdf")
    print(fn, ds.analysed_sst.shape, float(ds.latitude[218]), float(ds.longitude[601]), str(ds.time.values[0])[:10])
