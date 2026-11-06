# Final verification of the output files
import xarray as xr
import json

# Check NetCDF file
ds = xr.open_dataset('output/mhw_mask.nc')
print("NetCDF file created successfully:")
print(f"- Dimensions: {ds.dims}")
print(f"- Variables: {list(ds.data_vars.keys())}")
print(f"- Shape: {ds.mhw.shape}")

# Check report file
with open('output/report.json', 'r') as f:
    report = json.load(f)
print("\nReport file created successfully:")
print(f"- Region: {report['region']}")
print(f"- Baseline period: {report['baseline_analysed']}")
print(f"- Target period: {report['target_analysed']}")
print(f"- Number of events: {len(report['events'])}")

print("\nAnalysis complete and files verified!")