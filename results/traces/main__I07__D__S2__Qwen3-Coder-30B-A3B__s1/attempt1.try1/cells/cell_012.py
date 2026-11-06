import xarray as xr
import json
import numpy as np

# Check the generated NetCDF file
try:
    mhw_ds = xr.open_dataset('/work/output/mhw_mask.nc')
    print("=== NetCDF File Verification ===")
    print(f"Dataset: {mhw_ds}")
    print(f"Variable 'mhw' shape: {mhw_ds['mhw'].shape}")
    print(f"Time dimension: {mhw_ds['time'].shape}")
    print(f"Latitude dimension: {mhw_ds['latitude'].shape}")
    print(f"Longitude dimension: {mhw_ds['longitude'].shape}")
    print(f"Time range: {mhw_ds['time'].min().values} to {mhw_ds['time'].max().values}")
    print(f"Latitude range: {mhw_ds['latitude'].min().values} to {mhw_ds['latitude'].max().values}")
    print(f"Longitude range: {mhw_ds['longitude'].min().values} to {mhw_ds['longitude'].max().values}")
    
    # Check some sample values
    sample_mhw = mhw_ds['mhw'].values
    print(f"Sample values (first 3 days, first 3 lat/lon):")
    print(sample_mhw[:3, :3, :3])
    
    # Count MHW occurrences
    total_mhw_days = np.sum(sample_mhw)
    total_grid_points = sample_mhw.shape[1] * sample_mhw.shape[2]
    print(f"Total MHW days: {total_mhw_days}")
    print(f"Percentage of grid-point-days with MHW: {total_mhw_days/(sample_mhw.shape[0]*total_grid_points)*100:.2f}%")
    
except Exception as e:
    print(f"Error reading NetCDF: {e}")

# Check the report file
try:
    with open('/work/output/report.json', 'r') as f:
        report = json.load(f)
    print("\n=== Report File Verification ===")
    print(json.dumps(report, indent=2))
    
    # Validate required fields
    required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
    for field in required_fields:
        if field not in report:
            print(f"Missing required field: {field}")
        else:
            print(f"✓ Field '{field}' present")
            
    print(f"\nRegion: {report['region']}")
    print(f"Baseline period: {report['baseline_analysed']}")
    print(f"Target period: {report['target_analysed']}")
    print(f"Number of events: {len(report['events'])}")
    
except Exception as e:
    print(f"Error reading report: {e}")

print("\n=== Analysis Summary ===")
print("Marine Heatwaves detected in Baltic Sea region (54.45°N-55.65°N, 16.05°E-17.25°E)")
print("Period: June 1 - August 31, 2021")
print("Baseline period: January 1, 1992 - December 31, 2002")
print("Method: Copernicus Marine reprocessed SST product (level 4, daily)")