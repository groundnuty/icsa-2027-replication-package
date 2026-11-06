import os
import json
import xarray as xr

# Check if output directory exists and contains the files
if os.path.exists('output'):
    print("Output directory contents:")
    for file in os.listdir('output'):
        print(f"  {file}")
    
    # Check report.json content
    if os.path.exists('output/report.json'):
        with open('output/report.json', 'r') as f:
            report = json.load(f)
        print("\nReport content:")
        print(json.dumps(report, indent=2))
    
    # Check mhw_mask.nc
    if os.path.exists('output/mhw_mask.nc'):
        ds = xr.open_dataset('output/mhw_mask.nc')
        print("\nMHW mask dataset:")
        print(ds)
        print(f"\nMHW mask shape: {ds.mhw.shape}")
        print(f"MHW mask dimensions: {ds.mhw.dims}")
else:
    print("Output directory not found")