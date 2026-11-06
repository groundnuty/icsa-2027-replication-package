import h5py, numpy as np, xarray as xr
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
f = h5py.File(path, "r")
print(list(f.keys()))
d = f["analysed_sst"]
print(d.shape, d.dtype, d.chunks)
for k, v in d.attrs.items():
    print("attr", k, "=", v)
raw = d[3660, 373:433, 500:560]  # region slices guessed; verify indices
import xarray as xr
ds = xr.open_dataset(path, engine="h5netcdf")
lat = ds["latitude"].values; lon = ds["longitude"].values
la0 = int(np.where((lat >= 63.31) & (lat <= 64.51))[0][0])
lo0 = int(np.where((lon >= 21.31) & (lon <= 22.51))[0][0])
print("la0", la0, "lo0", lo0)
xr_slice = ds["analysed_sst"].isel(time=3660, latitude=slice(la0, la0+60), longitude=slice(lo0, lo0+60)).values
raw = d[3660, la0:la0+60, lo0:lo0+60]
print("raw dtype", raw.dtype, "equal:", np.array_equal(raw, xr_slice, equal_nan=True))
print("nan frac raw", np.isnan(raw).mean())
f.close()
