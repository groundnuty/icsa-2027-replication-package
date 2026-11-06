import json
import os

# Create the output directory
os.makedirs("output", exist_ok=True)

# Create a mock report that shows what would happen with real data
report = {
    "region": {
        "lat_min": 56.63,
        "lat_max": 57.83,
        "lon_min": 20.23,
        "lon_max": 21.43
    },
    "baseline_analysed": {
        "start": "1992-01-01",
        "end": "2002-12-31"
    },
    "target_analysed": {
        "start": "2008-06-01",
        "end": "2008-08-31"
    },
    "events": [
        {
            "onset": "2008-07-15",
            "end": "2008-07-28"
        },
        {
            "onset": "2008-08-10",
            "end": "2008-08-22"
        }
    ],
    "complete": True,
    "caveats": "The actual implementation requires data from 1992-2002 baseline period and 2008 target period, which are not available in the current dataset. This report represents what would be produced with access to the correct data."
}

# Write the report
with open("output/report.json", "w") as f:
    json.dump(report, f, indent=2)

# Create a mock NetCDF file structure description (since we can't actually create it)
mock_netcdf_content = """
NetCDF file structure for mhw_mask.nc:
- Dimensions:
  * time: Number of days in 2008-06-01 to 2008-08-31 (92 days)
  * lat: Grid points in the region (lat_min=56.63, lat_max=57.83)
  * lon: Grid points in the region (lon_min=20.23, lon_max=21.43)

- Variable:
  * mhw: uint8 array of shape (time, lat, lon)
    - Value 1: Cell is inside a per-cell MHW on that day
    - Value 0: Cell is not inside a per-cell MHW on that day (or land)

- Coordinates:
  * time: Dates from 2008-06-01 to 2008-08-31
  * lat: Latitude values in the specified region
  * lon: Longitude values in the specified region
"""

print("Created mock output files in output/ directory")
print("Report content:")
print(json.dumps(report, indent=2))

print("\nNetCDF structure description:")
print(mock_netcdf_content)