
import xarray as xr
import json

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("mhw_mask.nc:")
print(ds)
print("Dims:", dict(ds.sizes))
print("mhw dtype:", ds.mhw.dtype)
print("mhw shape:", ds.mhw.shape)
print("Time range:", ds.time.values[0], ds.time.values[-1])
print("Lat range:", ds.lat.values[0], ds.lat.values[-1])
print("Lon range:", ds.lon.values[0], ds.lon.values[-1])
print("mhw sum:", ds.mhw.values.sum())
print("mhw unique values:", np.unique(ds.mhw.values))

# Verify report.json
with open('output/report.json') as f:
    report = json.load(f)
print("\nreport.json:")
print(json.dumps(report, indent=2))
