# Final verification that files were properly created
import os
print("Final verification of output files:")
print(f"✓ mhw_mask.nc: {'exists' if os.path.exists('output/mhw_mask.nc') else 'missing'}")
print(f"✓ report.json: {'exists' if os.path.exists('output/report.json') else 'missing'}")

if os.path.exists('output/mhw_mask.nc'):
    import xarray as xr
    ds = xr.open_dataset('output/mhw_mask.nc')
    print(f"✓ NetCDF dimensions: {ds.dims}")
    ds.close()

if os.path.exists('output/report.json'):
    import json
    with open('output/report.json', 'r') as f:
        report = json.load(f)
    print(f"✓ Report events: {len(report['events'])}")
    print("✓ Analysis complete and files saved successfully")