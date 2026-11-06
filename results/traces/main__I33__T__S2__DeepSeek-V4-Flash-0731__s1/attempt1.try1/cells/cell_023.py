
import xarray as xr
import json

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc')
print("mhw_mask.nc:")
print(ds)
print()
print("mhw dtype:", ds.mhw.dtype)
print("mhw shape:", ds.mhw.shape)
print("mhw values:", np.unique(ds.mhw.values))
print("mhw sum:", ds.mhw.sum().values)
print()

# Verify report.json
with open('output/report.json') as f:
    report = json.load(f)
print("report.json:")
print(json.dumps(report, indent=2))
