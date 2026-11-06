
import xarray as xr
ds = xr.open_dataset('output/mhw_mask.nc')
print("Dims:", ds.mhw.dims)
print("Type of dims:", type(ds.mhw.dims))
print("Shape:", ds.mhw.shape)
print("Dtype:", ds.mhw.dtype)
print("Time range:", str(ds.time.values[0])[:10], "to", str(ds.time.values[-1])[:10])
print("Lat range:", ds.lat.values[0], "to", ds.lat.values[-1])
print("Lon range:", ds.lon.values[0], "to", ds.lon.values[-1])
print("Values:", sorted(set(ds.mhw.values.flatten().tolist())))
print("Sum:", int(ds.mhw.values.sum()))
