
import xarray as xr
import json

# Check mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("mhw_mask.nc:")
print(ds)
print("\nDims:", dict(ds.sizes))
print("Time:", ds.time.values[0], "to", ds.time.values[-1], "count:", len(ds.time))
print("Lat:", ds.lat.values[0], "to", ds.lat.values[-1], "count:", len(ds.lat))
print("Lon:", ds.lon.values[0], "to", ds.lon.values[-1], "count:", len(ds.lon))
print("mhw dtype:", ds.mhw.dtype)
print("mhw values unique:", set(np.unique(ds.mhw.values)))
print("mhw sum:", int(ds.mhw.values.sum()))

# Check report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)
print("\nreport.json:")
print(json.dumps(report, indent=2))
